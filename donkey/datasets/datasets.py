from os.path import dirname, realpath 
import os
import PIL

from ..sessions import SessionHandler

imgs_dir = dirname(dirname(realpath(__file__))+'/imgs/')
print(os.listdir(imgs_dir))


availible_sessions = ['sidewalk']


def load(session_name):

    sh = SessionHandler(imgs_dir)

    if session_name in availible_sessions:
        session = sh.load(session_name)
        return session
    else:
        raise ValueError('The dataset: %s, is not availible.' %dataset_name)