'''
Usage: 
    tflite_convert.py --model="mymodel.h5" --out="mymodel.tflite"

Note:
    my require tf-nightly if on tensorflow < 1.13
    pip install tf-nightly
'''
import os
import sys

from docopt import docopt
import tensorflow as tf

args = docopt(__doc__)

converter = tf.lite.TFLiteConverter.from_keras_model_file(args['--model'])
tflite_model = converter.convert()
open(args['--out'], "wb").write(tflite_model)

