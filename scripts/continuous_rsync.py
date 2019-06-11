import os
import time
from donkeycar.utils import load_config

cfg = load_config('config.py')

try:
    os.mkdir('cont_data')
except:
    pass

while True:
    command = "rsync -aW --progress %s@%s:%s/data/ ./cont_data/ --delete" %\
        (cfg.PI_USERNAME, cfg.PI_HOSTNAME, cfg.PI_DONKEY_ROOT)
    os.system(command)
    time.sleep(5)
