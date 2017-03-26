"""
explore.py

Used to train and test many different types of models to find the best one.

Usage:
    explore.py (--datasets=<dataset>) (--name=<name) [--loops=<loops]


Options:
  --url=<url>   url of the hdf5 dataset
  --datasets=<datasets>   file path of the hdf5 dataset
  --loops=<loops>   times to loop through the tests [default: 10]
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


def save_results(results, name):
    df = pd.DataFrame(all_results)
    results_path = os.path.join(dk.config.results_path, name + '.csv')
    df.to_csv(results_path, index=False)


args = docopt(__doc__)

if __name__ == '__main__':

    test_name = args['--name']
    loops = int(args['--loops'])

    test_dir_path = os.path.join(dk.config.results_path, test_name)
    dk.utils.make_dir(test_dir_path)


    #load data
    if args['--datasets'] is not None:
        datasets = args['--datasets'].split(',')
        datasets = [os.path.join(dk.config.datasets_path,d) for d in datasets]
        dataset_name = str(datasets)
        train, val, test = dk.datasets.split_datasets(datasets)
    

    #Define the model parameters you'd like to explore.

    dense1 = [{'units': 32, 'dropout': .2}]

    dense2 = [{'units': 64, 'dropout': .2}]


    conv1 = [
            {'filters': 8, 'kernal': (3,3), 'strides':(1,1), 'pool':(2,2)}, 
            {'filters': 16, 'kernal': (3,3), 'strides':(1,1), 'pool':(2,2)},
            {'filters': 32, 'kernal': (3,3), 'strides':(1,1), 'pool':(2,2)}
            ]

    conv2 = [
            {'filters': 8, 'kernal': (3,3), 'strides':(1,1), 'pool':(2,2)}, 
            {'filters': 16, 'kernal': (3,3), 'strides':(1,1), 'pool':(2,2)},
            {'filters': 32, 'kernal': (3,3), 'strides':(1,1), 'pool':(2,2)},
            {'filters': 32, 'kernal': (3,3), 'strides':(1,1), 'pool':(2,2)}
            ]

    model_params ={
             'conv': [ conv1, conv2, ],
             'dense':[ dense1, dense2 ],
            }


    batch_size = 64

    
    #create permutations of the models. 
    model_params = list(dk.utils.param_gen(model_params))

    param_count = len(model_params) * loops
    print('total params to test: %s' % param_count)

    all_results = []
    test_count = 0

    for i in range(loops):

        for mp in model_params:
            

            test_count += 1

            print('test %s of %s' %(test_count, param_count))

            results = {}
            results['dataset'] = dataset_name

            #MODEL
            model = dk.models.categorical_model_factory(**mp)
            model_path = os.path.join(test_dir_path, test_name + '_' + str(test_count))

            results['conv_layers'] = str(mp['conv'])
            results['dense_layers'] = str(mp['dense'])
            

            #DATASET
            train, val, test = dk.datasets.split_datasets(datasets, 
                                                          batch_size=batch_size)

            results['training_samples'] = train['n']
            results['validation_samples'] = val['n']
            results['test_samples'] = test['n']


            start = time.time()

            #train the model
            hist = dk.models.train_gen(model, model_path, train_gen=train['gen'], 
                                        val_gen=val['gen'] , steps=train['n']/batch_size, 
                                        epochs=100)

            model = keras.models.load_model(model_path)
            end = time.time()

            results['training_duration'] = end-start
            results['batch_size']=batch_size
            results['training_loss'] = model.evaluate_generator(train['gen'], 
                                            steps=1)

            results['training_loss_progress'] = hist.history
            results['epochs'] = len(hist.history['val_loss'])
            results['validation_loss'] = model.evaluate_generator(val['gen'], 
                                            steps=val['n']/batch_size)

            results['test_loss'] = model.evaluate_generator(test['gen'], 
                                            steps=test['n']/batch_size)
            results['model_params'] = model.count_params()


            all_results.append(results)
            
            test_results_path = os.path.join(test_dir_path, test_name)
            save_results(results, test_results_path)

            sys.stdout.flush()
