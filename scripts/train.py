"""
Example of how to train a keras model from simulated images or a 
previously recorded session.

Usage:
    train.py (--datasets=<datasets>) (--name=<name>) 


Options:
  --datasets=<datasets>   file path of dataset
  --name=<name>   name of model to be saved
"""

import os
import time
from docopt import docopt
import tempfile

import donkey as dk
from keras.callbacks import ModelCheckpoint
import keras

# Get args.


if __name__ == "__main__":
    args = docopt(__doc__)

    if args['--datasets'] is not None:
        datasets = args['--datasets'].split(',')
        datasets = [os.path.join(dk.config.datasets_path,d) for d in datasets]
        print('loading data from %s' %datasets)
        #X,Y = dk.sessions.hdf5_to_dataset(dataset_path)
        train, val, test = dk.datasets.split_datasets(datasets)
    
    model_name = args['--name']
   

    #Suggested model parameters    
    conv=[(8,3,3), (16,3,3), (32,3,3), (32,3,3)]
    dense=[32]
    dropout=.2
    learning_rate = .001
    decay = 0.0
    batch_size=32
    validation_split=0.1
    epochs = 100

    #Generate and compile model
    model = dk.models.cnn3_full1_relu(conv, dense, dropout)
    optimizer = keras.optimizers.Adam(lr=learning_rate, decay=decay)
    model.compile(optimizer=optimizer, loss='mean_squared_error')
                

    #train, val, test = dk.utils.split_dataset(X, Y, val_frac=.1, test_frac=0.0,
    #                                          shuffle=True, seed=1234)

    #X_train, Y_train = train
    #X_val, Y_val = val



    file_path = os.path.join(dk.config.models_path, model_name+".hdf5")

    #checkpoint to save model after each epoch
    save_best = keras.callbacks.ModelCheckpoint(file_path, monitor='val_loss', verbose=1, 
                                          save_best_only=False, mode='min')

    #stop training if the validation error stops improving.
    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=.0005, patience=4, 
                                         verbose=1, mode='auto')

    callbacks_list = [save_best, early_stop]


    hist = model.fit_generator(
                            train['gen'], 
                            samples_per_epoch=train['n'], 
                            nb_epoch=epochs, 
                            verbose=1, 
                            callbacks=callbacks_list, 
                            validation_data=val['gen'], 
                            nb_val_samples=val['n'])

    #hist = model.fit(X, Y, batch_size=batch_size, nb_epoch=epochs, 
    #                validation_data=(X_val, Y_val), callbacks=callbacks_list)
