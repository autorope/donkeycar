"""
Script to drive a TF model as fast as possible

Usage:
    profile.py (--model=<model>) (--type=<linear|categorical|etc>)
    
Options:
    -h --help        Show this screen.
"""
import os
from docopt import docopt
import donkeycar as dk
import numpy as np
import time
from donkeycar.utils import FPSTimer


def profile(model_path, model_type):
    cfg = dk.load_config('config.py')
    model_path = os.path.expanduser(model_path)
    model = dk.utils.get_model_by_type(model_type, cfg)
    model.load(model_path)
    
    count, h, w, ch = 1, cfg.TARGET_H, cfg.TARGET_W, cfg.TARGET_D
    seq_len = 0

    if "rnn" in model_type or "3d" in model_type:
        seq_len = cfg.SEQUENCE_LENGTH

    #generate random array in the right shape
    img = np.random.rand(int(h), int(w), int(ch)).astype(np.uint8)

    if seq_len:
        img_arr = []
        for i in range(seq_len):
            img_arr.append(img)
        img_arr = np.array(img_arr)

    #make a timer obj
    timer = FPSTimer()

    try:
        while True:

            '''
            run forward pass on model
            '''
            if seq_len:
                model.run(img_arr)
            else:
                model.run(img)

            '''
            keep track of iterations and give feed back on iter/sec
            '''
            timer.on_frame()

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    args = docopt(__doc__)
    profile(model_path = args['--model'], model_type = args['--type'])
