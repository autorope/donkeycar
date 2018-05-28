__version__ = '2.2.2'

print('using donkey v{} ...'.format(__version__))

import sys

if sys.version_info.major < 3:
    msg = 'Donkey Requires Python 3.4 or greater. You are using {}'.format(sys.version)
    raise ValueError(msg)

from . import parts
from .vehicle import Vehicle
from .memory import Memory
from . import utils
from . import config
from .config import load_config
