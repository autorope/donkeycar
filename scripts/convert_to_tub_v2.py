#!/usr/bin/env python3
'''
Usage:
    convert_to_tub_v2.py --tub=<path> --output=<path>

Note:
    This script converts the old datastore format, to the new datastore format.
'''

import json
import os
import traceback
from pathlib import Path

from docopt import docopt
from PIL import Image
from progress.bar import IncrementalBar

import donkeycar as dk
from donkeycar.parts.datastore import Tub as LegacyTub
from donkeycar.parts.tub_v2 import Tub


def convert_to_tub_v2(paths, output_path):
    if type(paths) is str:
        paths = [paths]
    legacy_tubs = [LegacyTub(path) for path in paths]
    output_tub = None
    print(f'Total number of tubs: {len(legacy_tubs)}')

    for legacy_tub in legacy_tubs:
        if not output_tub:
            output_tub = Tub(output_path, legacy_tub.inputs,
                             legacy_tub.types, list(legacy_tub.meta.items()))

        record_paths = legacy_tub.gather_records()
        bar = IncrementalBar('Converting', max=len(record_paths))
        prev_rec_num = None
        for record_path in record_paths:
            try:
                contents = Path(record_path).read_text()
                record = json.loads(contents)
                image_path = record['cam/image_array']
                rec_num = int(image_path.split('_')[0])
                image_path = os.path.join(legacy_tub.path, image_path)
                image_data = Image.open(image_path)
                record['cam/image_array'] = image_data
                # first record or they are continuous, just append
                if not prev_rec_num or rec_num == prev_rec_num + 1:
                    output_tub.write_record(record)
                    prev_rec_num = rec_num
                # otherwise fill the gap with dummy records
                else:
                    prev_rec_num += 1
                    while prev_rec_num < rec_num:
                        idx = output_tub.manifest.current_index
                        output_tub.write_record({})
                        output_tub.delete_record(idx)
                        prev_rec_num += 1
                bar.next()
            except Exception as exception:
                print(f'Ignoring record path {record_path}\n', exception)
                traceback.print_exc()


if __name__ == '__main__':
    args = docopt(__doc__)

    input_path = args["--tub"]
    output_path = args["--output"]
    paths = input_path.split(',')
    convert_to_tub_v2(paths, output_path)
