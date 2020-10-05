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
from donkeycar.utils import FPSTimer


def profile(model_path, model_type):
    cfg = dk.load_config('config.py')
    model_path = os.path.expanduser(model_path)
    model = dk.utils.get_model_by_type(model_type, cfg)
    model.load(model_path)
    
    h, w, ch = cfg.TARGET_H, cfg.TARGET_W, cfg.TARGET_D

    # generate random array in the right shape in [0,1)
    img = np.random.randint(0, 255, size=(h, w, ch))

    # make a timer obj
    timer = FPSTimer()

    try:
        while True:
            # run inferencing
            model.run(img)
            # time
            timer.on_frame()

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    args = docopt(__doc__)
    profile(model_path = args['--model'], model_type = args['--type'])
