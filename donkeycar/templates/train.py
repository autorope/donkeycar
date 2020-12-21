#!/usr/bin/env python3
"""
Scripts to train a model using tensorflow or pytorch.
Basic usage should feel familiar: train.py --tubs data/ --model models/mypilot.h5

Usage:
    train.py [--tubs=tubs] (--model=<model>) [--type=(linear|inferred|tensorrt_linear|tflite_linear)] [--framework=(tf|torch)] [--checkpoint=checkpoint]

Options:
    -h --help              Show this screen.
"""

from docopt import docopt
import donkeycar as dk


def main():
    args = docopt(__doc__)
    cfg = dk.load_config()
    tubs = args['--tubs']
    model = args['--model']
    model_type = args['--type']
    framework = args.get('--framework', 'tf')

    if framework == 'tf':
        from donkeycar.pipeline.training import train
        train(cfg, tubs, model, model_type)
    elif framework == 'torch':
        from donkeycar.parts.pytorch.torch_train import train
        checkpoint_path = args.get('--checkpoint', None)
        train(cfg, tubs, model, model_type, checkpoint_path=checkpoint_path)
    else:
        print("Unrecognized framework: {}. Please specify one of 'tf' or 'torch'".format(framework))

if __name__ == "__main__":
    main()
