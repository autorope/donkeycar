#!/usr/bin/env python3
"""
Usage:
    convert_to_tflite.py [-o | --overwrite] <model>...

Options:
    -h --help       Show this screen.
    -o --overwrite  Force overwriting existing TFLite files

Note:
    This script converts a keras (.keras or .h5) model into TFLite.
    Supports multiple input files.

"""

from docopt import docopt
from donkeycar.parts.interpreter import keras_model_to_tflite
from os.path import splitext, exists

if __name__ == '__main__':
    args = docopt(__doc__)
    model_path_list = args['<model.h5>']
    overwrite = args['-o'] or args['--overwrite']
    print(f"Found {len(model_path_list)} models to process.")
    print(f"Overwrite set to: {overwrite}.")
    count = 0
    for model_path in model_path_list:
        base_path, ext = splitext(model_path)
        if ext not in ['.h5', '.keras']:
            print(f"Can only convert '.h5' or '.keras' but not {ext}")
            continue
        tflite_filename = base_path + '.tflite'
        if exists(tflite_filename) and not overwrite:
            print(f"Found existing tflite mode {tflite_filename}, will skip. "
                  f"If you want to overwrite existing files, please specify "
                  f"the option --overwrite or -o ")
            continue
        keras_model_to_tflite(model_path, tflite_filename)
        count += 1
    print(f"Finished converting {count} models")
