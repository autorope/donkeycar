"""
Script to create a default configfiles

Usage:
    setup.py


"""


import os
import shutil
import configparser

from docopt import docopt

import donkey as dk



# Get args.
args = docopt(__doc__)

print('Setting up mydonkey folders.')
dk.config.setup_paths()

shutil.copyfile('./config/vehicle.ini', os.path.join(dk.config.my_path, 'vehicle.ini'))
