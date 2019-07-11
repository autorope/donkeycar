'''
Usage: 
    tflite_convert.py --model="mymodel.h5" --out="mymodel.tflite"

Note:
    may require tensorflow > 1.11 or
    pip install tf-nightly
'''
import os

from docopt import docopt
from donkeycar.parts.tflite import keras_model_to_tflite

args = docopt(__doc__)

in_model = os.path.expanduser(args['--model'])
out_model = os.path.expanduser(args['--out']) 
keras_model_to_tflite(in_model, out_model)

