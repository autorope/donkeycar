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


mydonkey_path = os.path.expanduser('~/mydonkey')
dk.utils.setup_mydonkey_paths(path=mydonkey_path)

shutil.copyfile('./config/vehicle.ini', os.path.join(mydonkey_path, 'vehicle.ini'))
