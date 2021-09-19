import atexit
import os
import time
from datetime import datetime
import json

import numpy as np
from PIL import Image

from donkeycar.parts.datastore_v2 import Manifest, ManifestIterator

from queue import Queue, Empty
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class Tub(object):
    """
    A datastore to store sensor data in a key, value format. \n
    Accepts str, int, float, image_array, image, and array data types.
    """

    def __init__(self, base_path, inputs=[], types=[], metadata=[],
                 max_catalog_len=1000, read_only=False):
        self.base_path = base_path
        self.images_base_path = os.path.join(self.base_path, Tub.images())
        self.inputs = inputs
        self.types = types
        self.metadata = metadata
        self.manifest = Manifest(base_path, inputs=inputs, types=types,
                                 metadata=metadata, max_len=max_catalog_len,
                                 read_only=read_only)
        self.input_types = dict(zip(self.inputs, self.types))
        # Create images folder if necessary
        if not os.path.exists(self.images_base_path):
            os.makedirs(self.images_base_path, exist_ok=True)

    def write_record_ts(self, record, timestamp_sec):
        """
        Can handle various data types including images.
        """
        contents = dict()
        for key, value in record.items():
            if value is None:
                continue
            elif key not in self.input_types:
                continue
            else:
                input_type = self.input_types[key]
                if input_type == 'float':
                    # Handle np.float() types gracefully
                    contents[key] = float(value)
                elif input_type == 'str':
                    contents[key] = value
                elif input_type == 'int':
                    contents[key] = int(value)
                elif input_type == 'boolean':
                    contents[key] = bool(value)
                elif input_type == 'nparray':
                    contents[key] = value.tolist()
                elif input_type == 'list' or input_type == 'vector':
                    contents[key] = list(value)
                elif input_type == 'image_array':
                    # Handle image array
                    image = Image.fromarray(np.uint8(value))
                    name = Tub._image_file_name(self.manifest.current_index, key)
                    image_path = os.path.join(self.images_base_path, name)
                    image.save(image_path)
                    contents[key] = name

        # Private properties    
        contents['_timestamp_ms'] = round(timestamp_sec * 1000)
        contents['_index'] = self.manifest.current_index
        contents['_session_id'] = self.manifest.session_id

        self.manifest.write_record(contents)

    def write_record(self, record):
        """
        write_record should be only used in single threaded mode, as the timestamp 
        will be generated on the current thread.
        """
        self.write_record_ts(record, time.time())


    def delete_records(self, record_indexes):
        self.manifest.delete_records(record_indexes)

    def delete_last_n_records(self, n):
        # build ordered list of non-deleted indexes
        all_alive_indexes = sorted(set(range(self.manifest.current_index))
                                   - self.manifest.deleted_indexes)
        to_delete_indexes = all_alive_indexes[-n:]
        self.manifest.delete_records(to_delete_indexes)

    def restore_records(self, record_indexes):
        self.manifest.restore_records(record_indexes)

    def close(self):
        self.manifest.close()

    def __iter__(self):
        return ManifestIterator(self.manifest)

    def __len__(self):
        return self.manifest.__len__()

    @classmethod
    def images(cls):
        return 'images'

    @classmethod
    def _image_file_name(cls, index, key, extension='.jpg'):
        key_prefix = key.replace('/', '_')
        name = '_'.join([str(index), key_prefix, extension])
        # Return relative paths to maintain portability
        return name


class TubWriter(object):
    """
    A Donkey part, which can write records to the datastore.
    """

    class TubRecordCached:
        """
        Simple helper for storeing record in a queue
        """
        def __init__(self, record, timestamp):
            self.record = record
            self.timestamp = timestamp

    def __init__(self, base_path, inputs=[], types=[], metadata=[],
                 max_catalog_len=1000):
        self.tub = Tub(base_path, inputs, types, metadata, max_catalog_len)
        self.record_queue = Queue()
        self.mutex = Lock()
        self.on = False

    def run(self, *args):
        assert len(self.tub.inputs) == len(args), \
            f'Expected {len(self.tub.inputs)} inputs but received {len(args)}'
        record = dict(zip(self.tub.inputs, args))
        self.tub.write_record(record)
        return self.tub.manifest.current_index

    def run_threaded(self, *args):
        assert len(self.tub.inputs) == len(args), \
            f'Expected {len(self.tub.inputs)} inputs but received {len(args)}'
        record = dict(zip(self.tub.inputs, args))
        # push the (record, timestamp) tuple into queue
        self.record_queue.put( (record, time.time()) )
        self.mutex.acquire()
        count = self.tub.manifest.current_index
        self.mutex.release()
        return count

    def dequeue_and_process_record(self):
        # pop a (record, timestamp) tuple
        record, timestamp = self.record_queue.get()
        # write the record to disk
        self.mutex.acquire()
        self.tub.write_record_ts(record, timestamp)
        self.mutex.release()
        # notify this task is done
        self.record_queue.task_done()

    def update(self):
        self.on = True
        # This loop runs like a 'normal' threaded loop 
        while self.on:
            if not self.record_queue.empty():
                try:
                    self.dequeue_and_process_record()
                except Empty:
                    logger.warn('Nothing to pop from record_queue. This should not be happening. Check if there is any other thread accessing record_queue.')

        # Main thread triggered shutdown(), finish up everything in the queue
        while not self.record_queue.empty():
            try:
                self.dequeue_and_process_record()
            except Empty:
                logger.warn('Nothing to pop from record_queue. This should not be happening. Check if there is any other thread accessing record_queue.')

    def close(self):
        self.record_queue.join()
        self.mutex.acquire()
        self.tub.close()
        self.mutex.release()
        # Force everything written to disk
        os.sync()

    def shutdown(self):
        self.on = False
        self.record_queue.join()
        self.close()


class TubWiper:
    """
    Donkey part which deletes a bunch of records from the end of tub.
    This allows to remove bad data already during recording. As this gets called
    in the vehicle loop the deletion runs only once in each continuous
    activation. A new execution requires to release of the input trigger. The
    action could result in a multiple number of executions otherwise.
    """
    def __init__(self, tub, num_records=20):
        """
        :param tub: tub to operate on
        :param num_records: number or records to delete
        """
        self._tub = tub
        self._num_records = num_records
        self._active_loop = False

    def run(self, is_delete):
        """
        Method in the vehicle loop. Delete records when trigger switches from
        False to True only.
        :param is_delete: if deletion has been triggered by the caller
        """
        # only run if input is true and debounced
        if is_delete:
            if not self._active_loop:
                # action command
                self._tub.delete_last_n_records(self._num_records)
                # increase the loop counter
                self._active_loop = True
        else:
            # trigger released, reset active loop
            self._active_loop = False