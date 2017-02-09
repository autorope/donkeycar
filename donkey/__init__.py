
import os
uname = os.uname()
if not uname[4].startswith("arm"):
    from . import (utils, 
                   models, 
                   datasets, 
                   remotes, 
                   sensors,
                   actuators,
                   mixers,
                   vehicles,
                   pilots,
                   templates,) 

else:
    print('Detected running on rasberrypi. Only importing select modules.')
    from . import actuators, mixers, remotes, sensors, vehicles
