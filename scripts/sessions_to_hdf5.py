"""
Create a single file containing the dataset of one or many sessions.

Usage:
    sessions_to_hdf5.py [--sessions=<name>] [--file_path=<name>]

Options:
  --sessions=<name>   sessions to combine (separated by commas, no spaces)
  --file_path=<name> name of dataset file to save.
"""

from docopt import docopt
import donkey as dk

if __name__ == '__main__':
    # Get args.
    
    args = docopt(__doc__)

    sessions_folder='~/mydonkey/sessions/'
    session_names = args['--sessions'].split(',')

    file_path = args['--file_path']


    X, Y = dk.sessions.sessions_to_dataset(sessions_folder=sessions_folder,
                                    session_names=session_names,
                                    )

    dk.sessions.dataset_to_hdf5(X, Y, file_path)
