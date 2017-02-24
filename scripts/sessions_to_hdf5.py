"""
Create a single file containing the dataset of one or many sessions.

Usage:
    upload.py (--sessions=<sessions>) (--file_path=<file_path>)

Options:
  --sessions=<sessions>   sessions to combine (separated by commas, no spaces)
  --file_path=<file_path> name of dataset file to save.
"""

import doctopt
import donkey as dk

if __name__ == '__main__':
    # Get args.
    args = docopt(__doc__)

    sessions_folder='~/mydonkey/sessions/'
    sessions = args['sessions'].split(',')

    file_path = args['file_path']


    dk.sessions.sessions_to_hdf5(sessions_folder=sessions_folder,
                                session_names=session_names,
                                file_path=file_path)

