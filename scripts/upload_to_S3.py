"""
Upload a file to S3 (requires amazon credentials).

Usage:
    upload_to_S3.py (--file_path=<file_path>) [--bucket=<bucket>] 

Options:
  --file_path=<file_path> name of dataset file to save.
  --bucket=<bucket>  name of S3 bucket to upload data. [default: donkey_resources].
"""

import math
import os
from docopt import docopt
import donkey as dk

import boto
from filechunkio import FileChunkIO
from boto.s3.key import Key

def upload_to_amazon(bucket_name, file_path):


    #Use environmental variables to authenticalt S3
    c = boto.connect_s3()
    b = c.get_bucket(bucket_name)

    file_name = os.path.basename(file_path)

    source_path = file_path
    source_size = os.stat(source_path).st_size

    # Create a multipart upload request
    mp = b.initiate_multipart_upload(file_name)

    # Use a chunk size of 50 MiB (feel free to change this)
    chunk_size = 52428800
    chunk_count = int(math.ceil(source_size / float(chunk_size)))

    # Send the file parts, using FileChunkIO to create a file-like object
    # that points to a certain byte range within the original file. We
    # set bytes to never exceed the original file size.
    for i in range(chunk_count):
        print('Uploading chunk %s of %s.' %(i+1, chunk_count))
        offset = chunk_size * i
        bytes = min(chunk_size, source_size - offset)
        with FileChunkIO(source_path, 'r', offset=offset,bytes=bytes) as fp:
            mp.upload_part_from_file(fp, part_num=i + 1)

    # Finish the upload
    mp.complete_upload()

    b.set_acl('public-read', file_name)

    url = get_s3_url(bucket_name, file_name)
    return url


def get_s3_url(bucket, key):
    base = 'https://s3.amazonaws.com'
    url = '/'.join([base, bucket, key])
    return url


if __name__ == '__main__':
    # Get args.
    args = docopt(__doc__)

    bucket = args['--bucket'] 
    file_path = args['--file_path']

    url = upload_to_amazon(bucket, file_path)

    print('Upload Complete: %s' %url)

