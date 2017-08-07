import os
import shutil

def make_path(rel_path):
    path = os.path.expanduser(rel_path)
    try:
        os.makedirs(path)
    except:
        pass

def copy_file(src, dest):
    dest_path = os.path.expanduser(dest)
    shutil.copyfile(src, dest_path)
        
make_path('~/mydonkey/datasets')
make_path('~/mydonkey/models')
copy_file('config/default.h5', '~/mydonkey/models/default.h5')
copy_file('config/vehicle.ini', '~/mydonkey/vehicle.ini')