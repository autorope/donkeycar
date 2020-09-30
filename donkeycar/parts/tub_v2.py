import json
import os
import time

import numpy as np
from PIL import Image

from donkeycar.parts.datastore_v2 import Manifest, ManifestIterator
from donkeycar.parts.part import Part


class Tub(object):
    '''
    A datastore to store sensor data in a key, value format. \n
    Accepts str, int, float, image_array, image, and array data types.
    '''
    def __init__(self, base_path, inputs=[], types=[], metadata=[], max_catalog_len=1000):
        self.base_path = base_path
        self.images_base_path = os.path.join(self.base_path, Tub.images())
        self.inputs = inputs
        self.types = types
        self.metadata = metadata
        self.manifest = Manifest(base_path, inputs=inputs, types=types, metadata=metadata, max_len=max_catalog_len)
        self.input_types = dict(zip(self.inputs, self.types))
        # Create images folder if necessary
        if not os.path.exists(self.images_base_path):
            os.makedirs(self.images_base_path, exist_ok=True)

    def write_record(self, record):
        '''
        Can handle various data types including images.
        '''
        contents = dict()
        for key, value in record.items():
            if value is None:
                continue
            elif not key in self.input_types:
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
        contents['_timestamp_ms'] = int(round(time.time() * 1000))
        contents['_index'] = self.manifest.current_index

        self.manifest.write_record(contents)

    def delete_record(self, record_index):
        self.manifest.delete_record(record_index)

    def delete_last_n_records(self, n):
        last_index = self.manifest.current_index
        first_index = last_index - n
        for index in range(first_index, last_index):
            if index < 0:
                continue
            else:
                self.manifest.delete_record(index)

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


class TubWriter(Part):
    '''
    A Donkey threaded part, which can write records to the datastore.
    '''
    def __init__(self, base_path, inputs=[], types=[], metadata=[], max_catalog_len=1000):
        self.tub = Tub(base_path, inputs, types, metadata, max_catalog_len)

    def run(self, *args):
        assert len(self.tub.inputs) == len(args)
        record = dict(zip(self.tub.inputs, args))
        self.tub.write_record(record)
        return self.tub.manifest.current_index

    def __iter__(self):
        return self.tub.__iter__()
