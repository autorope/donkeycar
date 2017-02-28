"""
Example of how to train a keras model from simulated images or a 
previously recorded session.

Usage:
    train.py (--sessions=<sessions>) [--epochs=<epochs>] 
    train.py (--url=<url>) [--epochs=<epochs>] 


Options:
  --sessions=<name>   session to train on
  --url=<url>   url of dataset
  --epochs=<epochs>   number of epochs [default: 20]
"""

import os
import time
from docopt import docopt

import donkey as dk
from keras.callbacks import ModelCheckpoint
import keras

# Get args.
args = docopt(__doc__)
#sessions_path = '~/donkey_data/sessions/'
#models_path = os.path.expanduser('~/donkey_data/models/')


if __name__ == "__main__":
    print(args)
    if args['--sessions'] is not None:
        sessions = args['--sessions'].split(',')
        X,Y = dk.sessions.sessions_to_dataset(sessions)
        dataset_name = sessions[0]
    elif args['--url'] is not None:
        url = args['--url']
        X, Y = dk.datasets.load_url(url)
        dataset_name = url.split('/')[-1]
    
    epochs = int(args['--epochs'])
   


    print('Loading Model.')
    
    conv=[(8,3,3), (16,3,3), (32,3,3), (32,3,3)]
    dense=[32]
    dropout=.2
    learning_rate = .0001
    decay = 0.0
    batch_size=128
    validation_split=0.2

    model = dk.models.cnn3_full1_relu(conv, dense, dropout)

    optimizer = keras.optimizers.Adam(lr=learning_rate, decay=decay)
    model.compile(optimizer=optimizer, loss='mean_squared_error')
                

    file_name="best-"+dataset_name+".hdf5"
    file_path = os.path.join(dk.config.models_path, file_name)

    checkpoint = ModelCheckpoint(file_path, monitor='val_loss', verbose=1, 
                                 save_best_only=False, mode='min')
    callbacks_list = [checkpoint]

    train, val, test = dk.utils.split_dataset(X, Y, shuffle=True)

    X_train, Y_train = train
    X_val, Y_val = val
    X_test, Y_test = test


    hist = model.fit(X, Y, batch_size=batch_size, nb_epoch=epochs, 
                    validation_data=(X_val, Y_val), callbacks=callbacks_list)


    print(trained_model.evaluate(X, Y))