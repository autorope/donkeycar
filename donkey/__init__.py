
import platform
uname = platform.platform()
if not 'armv7l' in uname:
    print('Loading modules for server.')
    from . import (utils, 
                   models, 
                   datasets, 
                   sessions,
                   remotes, 
                   sensors,
                   actuators,
                   mixers,
                   vehicles,
                   pilots,
                   templates,
                   config) 

else:
    print('Detected running on rasberrypi. Only importing select modules.')
    from . import (actuators, 
                   mixers, 
                   remotes, 
                   sensors, 
                   vehicles, 
                   config,
                   pilots,
                   models)
