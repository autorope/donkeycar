"""
Script to 

Usage:
    explore.py (--url=<url>) (--name=<name) [--loops=<loops]


Options:
  --url=<url>   url of the hdf5 dataset
  --loops=<loops>   times to loop through the tests [default: 1]
  --name=<name>  name of the test
"""


import os
import sys
import time
import itertools
import random


from docopt import docopt
import pandas as pd
import keras

import donkey as dk



def train_model(X, Y, model, batch_size=64, epochs=1, results=None, 
                shuffle=True, seed=None):

    '''
    Train a model, test it using common evaluation techiques and 
    record the results.
    '''
    #split data

    train, val, test = dk.utils.split_dataset(X, Y, shuffle=shuffle, seed=seed)

    X_train, Y_train = train
    X_val, Y_val = val
    X_test, Y_test = test

    results['training_samples'] = X_train.shape[0]
    results['validation_samples'] = X_val.shape[0]
    results['test_samples'] = X_test.shape[0]
    
    start = time.time()
    hist = model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=epochs, 
                     validation_data=(X_val, Y_val), verbose=0)    
    
    end = time.time()

    results['training_duration'] = end-start
    
    results['batch_size']=batch_size
    results['epochs'] = epochs
    results['training_loss'] = model.evaluate(X_train, Y_train, verbose=0)
    results['training_loss_progress'] = hist.history
    results['validation_loss'] = model.evaluate(X_val, Y_val, verbose=0)
    results['test_loss'] = model.evaluate(X_test, Y_test, verbose=0)
    results['model_params'] = model.count_params()
    
    return model, results



def save_results(results, name):
    df = pd.DataFrame(all_results)
    df.to_csv(name + '_training_results.csv')


args = docopt(__doc__)

if __name__ == '__main__':

    url = args['--url']
    name = args['--name']
    loops = int(args['--loops'])

    model_params ={
             'conv': [
                        [(8,3,3), (16,3,3), (32,3,3), (32,3,3)],
                        [(8,3,3), (16,3,3), (32,3,3)]
                    ],
             'dense': [ [32, 256]],
             'dropout': [.2]
            }

    optimizer_params = {
        'lr': [.001, .0001],
        'decay': [0.0]
    }

    training_params = {
        'batch_size': [128,32],
        'epochs': [20]
    }

    print('loading data from %s' %url)
    X, Y = dk.datasets.load_url(url)

    dataset_name = url.rsplit('/', 1)[-1]

    model_params = list(dk.utils.param_gen(model_params))
    optimizer_params = list(dk.utils.param_gen(optimizer_params))
    training_params = list(dk.utils.param_gen(training_params))

    param_count = len(model_params) * len(optimizer_params) * len(training_params) * loops

    print('total params to test: %s' % param_count)

    all_results = []
    test_count = 0

    for i in range(loops):
        seed = random.choise([1234, 2345, 3456, 4567])

        for mp in model_params:
            model = dk.models.cnn3_full1_relu(**mp)
            
            for op in optimizer_params:
                optimizer = keras.optimizers.Adam(**op)
                model.compile(optimizer=optimizer, loss='mean_squared_error')
                
                for tp in training_params:
                    test_count += 1
                    print('test %s of %s' %(test_count, param_count))
                    results = {}
                    results['dataset_name'] = dataset_name
                    results['random_seed'] = seed
                    results['conv_layers'] = str([i[0] for i in mp['conv']])
                    results['dense_layers'] = str([i for i in mp['dense']])
                    results['dropout'] = mp['dropout']
                    results['learning rate'] = op['lr']
                    results['decay'] = op['decay']
                    
                    
                    trained_model, results = train_model(X, Y[:,0], model, 
                                                         results=results, seed=seed, **tp)
                    

                    
                    all_results.append(results)
                    
                    save_results(results, name)

                    sys.stdout.flush()

