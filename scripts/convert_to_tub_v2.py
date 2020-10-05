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
    legacy_tubs = [LegacyTub(path) for path in paths]
    output_tub = None
    print('Total number of tubs: %s' % (len(legacy_tubs)))

    for legacy_tub in legacy_tubs:
        if not output_tub:
            output_tub = Tub(output_path, legacy_tub.inputs, legacy_tub.types, list(legacy_tub.meta.items()))

        record_paths = legacy_tub.gather_records()
        bar = IncrementalBar('Converting', max=len(record_paths))

        for record_path in record_paths:
            try:
                contents = Path(record_path).read_text()
                record = json.loads(contents)
                image_path = record['cam/image_array']
                image_path = os.path.join(legacy_tub.path, image_path)
                image_data = Image.open(image_path)
                record['cam/image_array'] = image_data
                output_tub.write_record(record)
                bar.next()
            except Exception as exception:
                print('Ignoring record path %s\n' % (record_path), exception)
                traceback.print_exc()


if __name__ == '__main__':
    args = docopt(__doc__)

    input_path = args["--tub"]
    output_path = args["--output"]
    paths = input_path.split(',')
    convert_to_tub_v2(paths, output_path)
