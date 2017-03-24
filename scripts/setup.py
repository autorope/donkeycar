"""
setup.py 

Run this once before doing anything to create a default 
folder structure and configfiles.

Usage:
    setup.py
"""


import os
import shutil
import configparser

from docopt import docopt

import donkey as dk



# Get args.
if __name__ == "__name__":
    args = docopt(__doc__)

    print('Setting up mydonkey folders.')
    dk.config.setup_paths()

    shutil.copyfile('./config/vehicle.ini', os.path.join(dk.config.my_path, 'vehicle.ini'))
    shutil.copyfile('./config/default.h5', os.path.join(dk.config.models_path, 'default.h5'))
