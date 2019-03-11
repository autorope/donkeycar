'''
Usage: 
    tflite_convert.py --model="mymodel.h5" --out="mymodel.tflite"

Note:
    may require tensorflow > 1.11 or
    pip install tf-nightly
'''
import os

from docopt import docopt
import tensorflow as tf

args = docopt(__doc__)

in_model = os.path.expanduser(args['--model'])
out_model = os.path.expanduser(args['--out']) 
converter = tf.lite.TFLiteConverter.from_keras_model_file(in_model)
tflite_model = converter.convert()
open(out_model, "wb").write(tflite_model)

