"""
Example of how to train a keras model from simulated images or a 
previously recorded session.

Usage:
    train.py (--sessions=<sessions>) [--epochs=<epochs>] 
    train.py (--url=<url>) [--epochs=<epochs>] 


Options:
  --sessions=<name>   session to train on
  --url=<url>   url of dataset
  --epochs=<epochs>   number of epochs [default: 50]
"""

import os
import time
from docopt import docopt

import donkey as dk
from keras.callbacks import ModelCheckpoint
import keras

# Get args.


if __name__ == "__main__":
    args = docopt(__doc__)

    #Load dataset from either sesions or url
    if args['--sessions'] is not None:
        sessions = args['--sessions'].split(',')
        X,Y = dk.sessions.sessions_to_dataset(sessions)
        dataset_name = sessions[0]
    elif args['--url'] is not None:
        url = args['--url']
        X, Y = dk.datasets.load_url(url)
        dataset_name = url.split('/')[-1]
    
    epochs = int(args['--epochs'])
   


    #Suggested model parameters    
    conv=[(8,3,3), (16,3,3), (32,3,3), (32,3,3)]
    dense=[32]
    dropout=.2
    learning_rate = .0001
    decay = 0.0
    batch_size=32
    validation_split=0.2

    #Generate and compile model
    model = dk.models.cnn3_full1_relu(conv, dense, dropout)
    optimizer = keras.optimizers.Adam(lr=learning_rate, decay=decay)
    model.compile(optimizer=optimizer, loss='mean_squared_error')
                

    file_name="best-"+dataset_name+".hdf5"
    file_path = os.path.join(dk.config.models_path, file_name)

    #checkpoint to save model after each epoch
    checkpoint = ModelCheckpoint(file_path, monitor='val_loss', verbose=1, 
                                 save_best_only=False, mode='min')
    callbacks_list = [checkpoint]


    hist = model.fit(X, Y, batch_size=batch_size, nb_epoch=epochs, 
                    validation_split=validation_split, callbacks=callbacks_list)


    print(trained_model.evaluate(X, Y))
