"""
Create a single file containing the dataset of one or many sessions.

Usage:
    sessions_to_hdf5.py (--sessions=<name>) (--name=<name>)

Options:
  --sessions=<name>   sessions to combine (separated by commas, no spaces)
  --name=<name> name of dataset file to save.
"""

import os
from docopt import docopt
import donkey as dk

if __name__ == '__main__':
    # Get args.
    
    args = docopt(__doc__)

    session_names = args['--sessions'].split(',')

    name = args['--name']

    file_path = os.path.join(dk.config.datasets_path, name)

    X, Y = dk.sessions.sessions_to_dataset(session_names=session_names)

    dk.sessions.dataset_to_hdf5(X, Y, file_path)
