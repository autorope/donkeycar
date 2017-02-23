"""
Example of how to train a keras model from simulated images or a 
previously recorded session.

Usage:
    train.py (--sessions=<sessions>) [--epochs=<epochs>] 


Options:
  --sessions=<name>   session to train on
  --epochs=<epochs>   number of epochs [default: 3].
"""

from docopt import docopt

import donkey as dk
from keras.callbacks import ModelCheckpoint
import keras

# Get args.
args = docopt(__doc__)

if __name__ == "__main__":
    print(args)
    sessions = args['--sessions'].split(',')
    epochs = int(args['--epochs'])
    #Train on session pictures
    sh = dk.sessions.SessionHandler(sessions_path='~/donkey_data/sessions/')
    s = sh.load(sessions[0])
    X, Y = s.load_dataset()


    #Train on simulated pictures
    #X, Y = dk.datasets.moving_square(n_frames=2000, return_x=True, return_y=False)


    #print('Downloading file, this could take some time.')
    #url = 'https://s3.amazonaws.com/donkey_resources/port.pkl'
    #X, Y = dk.datasets.load_url(url)

    print('Loading Model.')
    m = dk.models.cnn3_full1_relu()
    #m = keras.models.load_model('/home/wroscoe/donkey_data/models/best-diff_lines2.hdf5')


    filepath="best-"+sessions[0]+".hdf5"
    checkpoint = ModelCheckpoint(filepath, monitor='val_loss', verbose=1, 
                                 save_best_only=True, mode='min')
    callbacks_list = [checkpoint]

    hist = m.fit(X, Y, batch_size=64, nb_epoch=epochs, 
                     validation_split=.2, callbacks=callbacks_list)
