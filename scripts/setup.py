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

def make_dir(path):
    real_path = os.path.expanduser(path)
    print('making dir ', real_path)
    if not os.path.exists(real_path):
        os.makedirs(real_path)
    return real_path


# Get args.
if __name__ == "__main__":
    """
    This script sets up the folder struction for donkey to work. 
    It must run without donkey installed so that people installing with
    docker can build the folder structure for docker to mount to.
    """
    
    dk_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    dk_config_path = os.path.join(dk_path, 'config')
    dk_config_file_path = os.path.join(dk_config_path, "vehicle.ini")
    
    print('Reading config file...' + dk_config_file_path)
    cfg = configparser.ConfigParser()
    cfg.read(dk_config_file_path)
    mydonkey_path = os.path.expanduser(cfg['mydonkey'].get('path'))
    mydonkey_folders = cfg['mydonkey'].get('folders').split(',')
    
    print("Making 'mydonkey' folders to hold training data and pilot models.")
    make_dir(mydonkey_path)
    folder_paths = [os.path.join(mydonkey_path, f) for f in mydonkey_folders]   
    for fp in folder_paths:
        make_dir(fp)
        
    print("Copying config file.")
    file_name = os.path.basename(dk_config_file_path)
    mydonkey_config_file_path = os.path.join(mydonkey_path, file_name)
    shutil.copyfile(dk_config_file_path, mydonkey_config_file_path)
    print(mydonkey_config_file_path)

    print("Copying default autopilot.")
    file_name = "default.h5"
    mydonkey_models_folder = os.path.join(mydonkey_path, 'models')
    dk_model_file_path = os.path.join(dk_config_path, file_name)
    mydonkey_model_file_path = os.path.join(mydonkey_models_folder, file_name)
    shutil.copyfile(dk_model_file_path, mydonkey_model_file_path)

    print("Donkey setup complete.")
