# Author: Pierre Dumas, November 2017
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import multiprocessing
import time
import os
import sys
import boto3
import datetime
import pytz


'''
    s3uploader performs rsync like operation from a source local directory to an s3 bucket. As a class it spawns 
    worker processes that does the rsync periodically. Hashing filenames determines which work handles which files.    

    Usage as a class
    ----------------
    process = S3Uploader(5, 10, "/home/ubuntu", "my_bucket" )
    process.start()
    ..do something else for a while..
    process.shutdown()


    Usage as a CLI
    --------------
    pyton s3uploader 5 10 /home/ubuntu my_bucket

'''

class Worker(multiprocessing.Process):


    def __init__(self, worker_number, num_of_workers, bucket_files, local_dir, remote_bucket, compare_time, debug):
        self.num_of_workers = num_of_workers
        self.worker_number = worker_number
        self.bucket_files = bucket_files
        self.local_dir = local_dir
        self.remote_bucket = remote_bucket
        self.compare_time = compare_time
        self.debug = debug
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()
        self.client = boto3.client('s3')

    #
    # walk the local directory and upload any file that is not present in the s3 
    # listing, or which have changed in terms of size or last_modified
    #
    def run(self):

        for root, dirs, files in os.walk(self.local_dir):

            for filename in files:

                # hashing the filename determines of it will be handled by this thread
                if hash(filename) % self.num_of_workers != self.worker_number:
                    continue

                # construct the full local path
                local_path = os.path.join(root, filename)

                local_size = os.stat(local_path).st_size
                local_last_modified = datetime.datetime.fromtimestamp(os.stat(local_path).st_mtime).replace(tzinfo=pytz.UTC)


                # construct the full path
                relative_path = os.path.relpath(local_path, self.local_dir)

                # if the local file is also in s3
                if relative_path in self.bucket_files:

                    # stats of the s3 file 
                    remote_size = self.bucket_files[relative_path]['Size']
                    remote_last_modified = self.bucket_files[relative_path]['LastModified']

                    # if the local file has a different size, update s3 file
                    if (local_size > remote_size):
                        self.client.upload_file(local_path, self.remote_bucket,relative_path)
                        if self.debug:
                            print("worker " + str(self.worker_number) + " "  + str(relative_path) + " has different size, updating to s3 ")

                    # if the local file has been modified recently, update s3 file
                    elif local_last_modified > remote_last_modified  and self.compare_time==True:
                        self.client.upload_file(local_path, self.remote_bucket,relative_path)
                        if self.debug:
                            print("worker " + str(self.worker_number) + " "  + str(relative_path)) + " has been modified more recently, updating to s3"

                # otherwise the local file is new, upload to s3
                else:
                    self.client.upload_file(local_path, self.remote_bucket, relative_path)
                    if self.debug:
                        print("worker " + str(self.worker_number) + " "  + "uploading new file " + str(relative_path))



class S3Uploader(multiprocessing.Process):


    # num_of_workers  the number of child processes doing the upload 
    # periodicity:    the interval in seconds between sync to s3
    # local_dir:      the local directory path to sync to s3:  "/home/ubuntu/d2/data"
    # remote_bucket:  the name of the bucket:  "robocar-data"
    #
    def __init__(self, num_of_workers, periodicity, local_dir, remote_bucket, compare_time=False, debug=False):
        self.num_of_workers = num_of_workers
        self.periodicity = periodicity
        self.local_dir = local_dir
        self.remote_bucket = remote_bucket
        self.compare_time = compare_time
        self.debug = debug
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()
        self.client = boto3.client('s3')

    #
    # get a list of all filenames in the s3 bucket along with their size and last_modified
    #
    def get_bucket_files(self):
        
        #create a reusable Paginator
        paginator = self.client.get_paginator('list_objects')

        # Create a PageIterator from the Paginator
        page_iterator = paginator.paginate(Bucket=self.remote_bucket)

        # will hold all the s3 keys
        bucket_files = {}

        # call s3 to get list of files, 1000 at a time max
        for page in page_iterator:
            if 'Contents' in page:
                files_array = page['Contents']
                num = len(files_array)

                for i in xrange(0, num):
                    f = {}
                    f['Key'] = files_array[i]['Key']
                    f['Size'] = files_array[i]['Size']
                    f['LastModified'] = files_array[i]['LastModified']
                    bucket_files[f['Key']] = f
       
        #print("s3 bucket has " + str(len(bucket_files)) + " files") 
        return bucket_files
   
    # main runloop 
    def run(self):

        while not self.exit.is_set():
            try:
                # get all files keys in s3
                bucket_files = self.get_bucket_files()
    
                workers = []

                # spawn workers
                for i in xrange(0, self.num_of_workers):
                    w = Worker(i, self.num_of_workers , bucket_files, self.local_dir, self.remote_bucket, self.compare_time, self.debug)
                    w.start()
                    workers.append(w)

                # wait on workers to finish
                for i in xrange(0, self.num_of_workers):
                    workers[i].join()

            except Exception as e:             
                print("s3uploader received an exception while synching with s3" + str(e))
                pass                

            time.sleep(self.periodicity)


    #
    # to terminate uploader process
    #
    def shutdown(self): 
        self.exit.set()
        process.join()

if __name__ == '__main__':

    if len(sys.argv) !=  5:
        print("usage: python s3uploader <num of workers> <periodicity> <local_dir> <bucket>")
        exit(1)

    process = S3Uploader(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4], False, True)
    process.run()
    time.sleep(100)
    process.shutdown()




