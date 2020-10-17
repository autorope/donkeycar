#!/usr/bin/env python3
'''
Usage:
    convert_to_tub_v2.py --tub=<path> --output=<path> [--include_name]

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

from donkeycar.parts.datastore import Tub as LegacyTub
from donkeycar.parts.tub_v2 import Tub


def convert_to_tub_v2(paths, output_path, include_tub_name=False):
    legacy_tubs = [LegacyTub(path) for path in paths]
    output_tub = None
    print('Total number of tubs: %s' % (len(legacy_tubs)))

    for legacy_tub in legacy_tubs:
        if not output_tub:
            inputs = legacy_tub.inputs
            types = legacy_tub.types
            if include_tub_name:
                inputs.append('tub_name')
                types.append('str')
            output_tub = Tub(output_path, inputs, types,
                             list(legacy_tub.meta.items()))

        record_paths = legacy_tub.gather_records()
        legacy_path = os.path.normpath(legacy_tub.path)
        bar = IncrementalBar('Converting', max=len(record_paths))

        for record_path in record_paths:
            try:
                contents = Path(record_path).read_text()
                record = json.loads(contents)
                image_path = record['cam/image_array']
                image_path = os.path.join(legacy_tub.path, image_path)
                image_data = Image.open(image_path)
                record['cam/image_array'] = image_data
                if include_tub_name:
                    record['tub_name'] = legacy_path
                output_tub.write_record(record)
                bar.next()
            except Exception as exception:
                print('Ignoring record path %s\n' % record_path, exception)
                traceback.print_exc()


if __name__ == '__main__':
    args = docopt(__doc__)

    input_path = args["--tub"]
    output_path = args["--output"]
    include_name = args["--include_name"]
    paths = input_path.split(',')
    convert_to_tub_v2(paths, output_path, include_tub_name=include_name)
