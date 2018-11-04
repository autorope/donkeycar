import os

# Print version being used.
package_path = os.path.dirname(os.path.dirname(__file__))
version_path = os.path.join(package_path, 'VERSION')
with open(version_path, 'r') as f:
    version = f.read()
print('using donkey version: {} ...'.format(version))


import sys
current_module = sys.modules[__name__]


if sys.version_info.major < 3:
    msg = 'Donkey Requires Python 3.4 or greater. You are using {}'.format(sys.version)
    raise ValueError(msg)

from . import parts
from .vehicle import Vehicle
from .memory import Memory
from . import util
from . import config
from .config import load_config
