import os

def make_path(rel_path):
    path = os.path.expanduser(rel_path)
    try:
        os.makedirs(path)
    except:
        pass
        
make_path('~/mydonkey/datasets')
make_path('~/mydonkey/models')
