"""
Example of how to train a keras model from simulated images or a 
previously recorded session.

Usage:
    train.py [--datasets=<datasets>] [--sessions=<sessions>] (--name=<name>) 


Options:
  --datasets=<datasets>   file path of dataset
  --sessions=<sessions>   file path of sessions
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

    batch_size = 128

    if args['--datasets'] is not None:
        datasets = args['--datasets'].split(',')
        datasets = [os.path.join(dk.config.datasets_path,d) for d in datasets]
        print('loading data from %s' %datasets)
        train, val, test = dk.datasets.split_datasets(datasets, val_frac=.1, test_frac=.1, batch_size=128)
    
    elif args['--sessions'] is not None:
        session_names = args['--sessions'].split(',')
        X, Y = dk.sessions.sessions_to_dataset(session_names=session_names)
        dataset_path = os.path.join(dk.config.datasets_path, 'temp.h5')
        dk.sessions.dataset_to_hdf5(X, Y, dataset_path)
        datasets = [dataset_path]
        train, val, test = dk.datasets.split_datasets(datasets, val_frac=.1, test_frac=.1, batch_size=128)

    steps = round(train['n'] / batch_size)


    model_name = args['--name']
   
    #create model
    model = dk.models.categorical_model_factory(**dk.models.nvidia_arch)

    #path to save the model
    model_path = os.path.join(dk.config.models_path, model_name+".hdf5")

    #train the model
    dk.models.train_gen(model, model_path, train_gen=train['gen'], val_gen=val['gen'] , steps=n)