#!/usr/bin/env python3
"""
Scripts to train a keras model using tensorflow.
Basic usage should feel familiar: train.py --tubs data/ --model models/mypilot.h5

Usage:
    train.py  [--tubs=tubs] (--model=<model>)
    [--type=(linear|inferred|tensorrt_linear|tflite_linear)] 
    [--transfer=<transfer_model>]
    [--comment=<comment>]


Options:
    -h --help              Show this screen.
"""

from docopt import docopt
import donkeycar as dk
from donkeycar.pipeline.training import train


def main():
    args = docopt(__doc__)
    cfg = dk.load_config()
    tubs =  args['--tubs']
    if tubs == None:
        tubs = 'data/'
    model = args['--model']
    model_type = args['--type']
    transfer = args['--transfer']
    comment = args['--comment']
    
    train(cfg, tubs, model, model_type, transfer, comment)


if __name__ == "__main__":
    main()
