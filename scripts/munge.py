"""
Script to provide commond line access to data manipulation functions. 

Usage:
    munge.py [--sessions=<name>] 


Options:
  --remote=<name>   recording session name
"""

import donkey as dk

dk.sessions.pickle_sessions(sessions_folder='/home/wroscoe/donkey_data/sessions/',
                            session_names=['ac_1130', 'ac_1150', 'ac_1240'],
                                           #'wr_1030', 'wr_1115', 'wr_1150', 'wr_1240',]
                            file_path='/home/wroscoe/scale10-adam_cleaned.pkl')