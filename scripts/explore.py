"""
Script to 

Usage:
    explore.py (--url=<url>) 


Options:
  --url=<url>   url of the hdf5 dataset
"""


import os
import time
import itertools

from docopt import docopt
import pandas as pd
import keras

import donkey as dk


def train_model(X, Y, model, batch_size=64, epochs=1, results=None, shuffle=True):
    '''
    Train a model, test it using common evaluation techiques and 
    record the results.
    '''
    #split data
    train, val, test = dk.utils.split_dataset(X, Y, shuffle=shuffle)
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
    results['training_loss'] = model.evaluate(X_train, Y_train)
    results['training_loss_progress'] = hist.history
    results['validation_loss'] = model.evaluate(X_val, Y_val)
    results['test_loss'] = model.evaluate(X_test, Y_test)
    results['model_params'] = model.count_params()
    
    return model, results



def save_results(results):
    df = pd.DataFrame(all_results)
    df.to_csv('training_results.csv')


args = docopt(__doc__)

if __name__ == '__main__':

    url = args['--url']



    model_params ={
             'conv': [
                        [(8,3,3), (16,3,3), (32,3,3)],
                        #[(4,3,3),(8,3,3), (16,3,3), (32,3,3)],
                        #[(2,3,3), (4,3,3), (8,3,3), (16,3,3), (32,3,3)]
                    ],
             'dense': [ [64], [128]],
             'dropout': [.2]
            }

    optimizer_params = {
        'lr': [.001],
        'decay': [0.0]
    }

    training_params = {
        'batch_size': [32],
        'epochs': [1]
    }



    X, Y = dk.datasets.load_url('https://s3.amazonaws.com/donkey_resources/wr_feb_race_15deg_wide.hdf5')

    optimizer = keras.optimizers.Adam(lr=0.01, decay=0.0)

    all_results = []
    for mp in dk.utils.param_gen(model_params):
        model = dk.models.cnn3_full1_relu(**mp)
        
        for op in dk.utils.param_gen(optimizer_params):
            optimizer = keras.optimizers.Adam(**op)
            model.compile(optimizer=optimizer, loss='mean_squared_error')
            
            for tp in dk.utils.param_gen(training_params):
                results = {}
                results['conv_layers'] = str([i[0] for i in mp['conv']])
                results['dense_layers'] = str([i for i in mp['dense']])
                results['dropout'] = mp['dropout']
                results['learning rate'] = op['lr']
                results['decay'] = op['decay']
                
                
                trained_model, results = train_model(X, Y[:,0], model, 
                                                     results=results, **tp)
                

                
                all_results.append(results)
                
                save_results(results)
