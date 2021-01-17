#!/usr/bin/env python3
'''
Usage:
    convert_to_tub_v2.py --tub=<path> --output=<path>

Note:
    This script converts the old datastore format to the new datastore format.
'''

import json
import os
import traceback
from pathlib import Path

from docopt import docopt
from PIL import Image
from progress.bar import IncrementalBar

from donkeycar.parts.datastore import Tub as LegacyTub
from donkeycar.parts.tub_v2 import Tub


def convert_to_tub_v2(paths, output_path):
    """
    Convert from old tubs to new one

    :param paths:               legacy tub paths
    :param output_path:         new tub output path
    :return:                    None
    """
    empty_record = {'__empty__': True}
    if type(paths) is str:
        paths = [paths]
    legacy_tubs = [LegacyTub(path) for path in paths]
    print(f'Total number of tubs: {len(legacy_tubs)}')

    for legacy_tub in legacy_tubs:
        # add input and type for empty records recording
        inputs = legacy_tub.inputs + ['__empty__']
        types = legacy_tub.types + ['boolean']
        output_tub = Tub(output_path, inputs, types,
                         list(legacy_tub.meta.items()))
        record_paths = legacy_tub.gather_records()
        bar = IncrementalBar('Converting', max=len(record_paths))
        previous_index = None
        for record_path in record_paths:
            try:
                contents = Path(record_path).read_text()
                record = json.loads(contents)
                image_path = record['cam/image_array']
                current_index = int(image_path.split('_')[0])
                image_path = os.path.join(legacy_tub.path, image_path)
                image_data = Image.open(image_path)
                record['cam/image_array'] = image_data
                # first record or they are continuous, just append
                if not previous_index or current_index == previous_index + 1:
                    output_tub.write_record(record)
                    previous_index = current_index
                # otherwise fill the gap with empty records
                else:
                    # Skipping over previous record here because it has
                    # already been written.
                    previous_index += 1
                    # Adding empty record nodes, and marking them deleted
                    # until the next valid record.
                    delete_list = []
                    while previous_index < current_index:
                        idx = output_tub.manifest.current_index
                        output_tub.write_record(empty_record)
                        delete_list.append(idx)
                        previous_index += 1
                    output_tub.delete_records(delete_list)
                bar.next()
            except Exception as exception:
                print(f'Ignoring record path {record_path}\n', exception)
                traceback.print_exc()
        # writing session id into manifest metadata
        output_tub.close()


if __name__ == '__main__':
    args = docopt(__doc__)

    input_path = args["--tub"]
    output_path = args["--output"]
    paths = input_path.split(',')
    convert_to_tub_v2(paths, output_path)
