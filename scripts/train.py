"""
Example of how to train a keras model from simulated images or a 
previously recorded session.

Usage:
    train.py (--sessions=<sessions>) (--name=<name>)
    train.py (--url=<url>) (--name=<name>) 
    train.py (--dataset=<dataset>) (--name=<name>) 


Options:
  --sessions=<sessions>   session to train on
  --url=<url>   url of dataset
  --dataset=<dataset>   file path of dataset
  --name=<name>   name of model to be saved
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
    elif args['--url'] is not None:
        url = args['--url']
        X, Y = dk.datasets.load_url(url)
    elif args['--dataset'] is not None:
        dataset_path = args['--dataset']
        print('loading data from %s' %dataset_path)
        X,Y = dk.sessions.hdf5_to_dataset(dataset_path)
    
    model_name = args['--name']
   

    #Suggested model parameters    
    conv=[(8,3,3), (16,3,3), (32,3,3), (32,3,3)]
    dense=[32]
    dropout=.2
    learning_rate = .0001
    decay = 0.0
    batch_size=32
    validation_split=0.1
    epochs = 100

    #Generate and compile model
    #model = dk.models.cnn3_full1_relu(conv, dense, dropout)
    model = dk.models.conv_dense_sigmoid(conv, dense, dropout)
                

    train, val, test = dk.utils.split_dataset(X, Y, val_frac=.1, test_frac=0.0,
                                              shuffle=True, seed=1234)

    X_train, Y_train = train
    X_val, Y_val = val

    if model.output_shape[1] > 1:
        Y_train = dk.utils.bin_Y(Y_train)
        Y_val = dk.utils.bin_Y(Y_val)


    file_path = os.path.join(dk.config.models_path, model_name+".hdf5")

    #checkpoint to save model after each epoch
    save_best = keras.callbacks.ModelCheckpoint(file_path, monitor='val_loss', verbose=1, 
                                          save_best_only=False, mode='min')

    #stop training if the validation error stops improving.
    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=.0005, patience=4, 
                                         verbose=1, mode='auto')

    callbacks_list = [save_best, early_stop]


    hist = model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=epochs, 
                    validation_data=(X_val, Y_val), callbacks=callbacks_list)


    print(model.evaluate(X, Y))
