"""
Script to 

Usage:
    explore.py (--datasets=<dataset>) (--name=<name) [--loops=<loops]


Options:
  --url=<url>   url of the hdf5 dataset
  --datasets=<datasets>   file path of the hdf5 dataset
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
from keras import callbacks

import donkey as dk




def save_results(results, name):
    df = pd.DataFrame(all_results)
    results_path = os.path.join(dk.config.results_path, name + '.csv')
    df.to_csv(results_path, index=False)


args = docopt(__doc__)

if __name__ == '__main__':

    if args['--datasets'] is not None:
        datasets = args['--datasets'].split(',')
        datasets = [os.path.join(dk.config.datasets_path,d) for d in datasets]
        dataset_name = str(datasets)
        print('loading data from %s' %datasets)
        #X,Y = dk.sessions.hdf5_to_dataset(dataset_path)
        train, val, test = dk.datasets.split_datasets(datasets)
    

    name = args['--name']
    loops = int(args['--loops'])


    #Define the model parameters you'd like to explore.
    model_params ={
             'conv': [
                        [(8,3,3), (16,3,3), (32,3,3), (32,3,3)],
                        [(8,3,3), (16,3,3), (32,3,3), (64,3,3)],
                        [(8,3,3), (16,3,3), (32,3,3)]
                    ],
             'dense': [ [32], [256], [128]],
             'dropout': [.2, .4]
            }

    optimizer_params = {
        'lr': [.001, .0001],
        'decay': [0.0]
    }

    training_params = {
        'batch_size': [128,32],
        'epochs': [1]
    }

    

    model_params = list(dk.utils.param_gen(model_params))
    optimizer_params = list(dk.utils.param_gen(optimizer_params))
    training_params = list(dk.utils.param_gen(training_params))

    param_count = len(model_params) * len(optimizer_params) * len(training_params) * loops

    print('total params to test: %s' % param_count)

    all_results = []
    test_count = 0

    for i in range(loops):
        seed = random.choice([1234, 2345, 3456, 4567])

        for mp in model_params:
            
            
            for op in optimizer_params:

                for tp in training_params:
                    model = dk.models.cnn3_full1_relu(**mp)
                    optimizer = keras.optimizers.Adam(**op)
                    model.compile(optimizer=optimizer, loss='mean_squared_error')
                    test_count += 1
                    print('test %s of %s' %(test_count, param_count))
                    results = {}
                    results['dataset'] = dataset_name
                    results['random_seed'] = seed
                    results['conv_layers'] = str(['{},{}'.format(i[0], i[1]) for i in mp['conv']])
                    results['dense_layers'] = str([i for i in mp['dense']])
                    results['dropout'] = mp['dropout']
                    results['learning_rate'] = op['lr']
                    results['decay'] = op['decay']
                    
                    
                    train, val, test = dk.datasets.split_datasets(datasets, 
                                                                  batch_size=tp['batch_size'])

                    results['training_samples'] = train['n']
                    results['validation_samples'] = val['n']
                    results['test_samples'] = test['n']
                    

                    #stop training if the validation loss doesn't improve for 5 consecutive epochs.
                    early_stop = callbacks.EarlyStopping(monitor='val_loss', min_delta=.001, patience=2, 
                                                         verbose=1, mode='auto')

                    callbacks_list = [early_stop]

                    start = time.time()
                    hist = model.fit_generator(
                                            train['gen'], 
                                            samples_per_epoch=train['n'], 
                                            nb_epoch=tp['epochs'], 
                                            verbose=1, 
                                            callbacks=callbacks_list, 
                                            validation_data=val['gen'], 
                                            nb_val_samples=val['n'])


                    end = time.time()

                    results['training_duration'] = end-start
                    
                    results['batch_size']=tp['batch_size']
                    results['training_loss'] = model.evaluate_generator(train['gen'], 
                                                    val_samples=train['n'])
                    results['training_loss_progress'] = hist.history
                    results['epochs'] = len(hist.history['val_loss'])
                    results['validation_loss'] = model.evaluate_generator(val['gen'], 
                                                    val_samples=val['n'])

                    results['test_loss'] = model.evaluate_generator(test['gen'], 
                                                    val_samples=test['n'])
                    results['model_params'] = model.count_params()


                    all_results.append(results)
                    
                    save_results(results, name)

                    sys.stdout.flush()

