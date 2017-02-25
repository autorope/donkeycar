"""
A script designed to run train multiple models on multiple datasets. This 
can be helpful if you use a paid GPU instance from amazon and want to use 
the resource efficiently.

Features:
* Saves best model each epoch.
* 
"""

import os

from operator import itemgetter

import donkey as dk
from keras.callbacks import ModelCheckpoint

sh = dk.sessions.SessionHandler('/home/wroscoe/donkey_data/sessions/')
s = sh.load('diff_lines')

#datasets we want to test

#datasets = {'square': dk.datasets.moving_square(1000, return_y=False)}
#datasets = {'square': dk.datasets.load_file('/home/wroscoe/code/notebooks/whiteline_dataset.pkl')}
datasets = {'diff_lines': s.load_dataset()}


#the models we want to test
models = {
            'cnn3_full1_rnn1': dk.models.cnn3_full1_rnn1(),
            'cnn3_full1': dk.models.cnn3_full1(),
            'cnn3_full1_linear_tanh': dk.models.cnn3_full1_linear_tanh(),
            'cnn3_full1_tanh_tanh': dk.models.cnn3_full1_tanh_tanh(),
            'cnn3_full1_2dense_linear_tanh':dk.models.cnn3_full1_2dense_linear_tanh(),

        }


results = []

for ds_name, ds in datasets.items():
    print('Using dataset: %s' %ds_name)

    for m_name, m in models.items(): 
        print('Using model: %s' %m_name)
        
        filepath="best-weights.hdf5"
        checkpoint = ModelCheckpoint(filepath, monitor='val_loss', verbose=1, 
                                     save_best_only=True, mode='min')
        callbacks_list = [checkpoint]

        X, Y = ds

        hist = m.fit(X, Y, batch_size=32, nb_epoch=25, 
                         validation_split=.2, callbacks=callbacks_list)
        
        print(hist.history)
        result = {'model_name': m_name, 'dataset_name': ds_name, 
                  'min_val_loss': min(hist.history['val_loss'])
                 }
        results.append(result)

        
        val_loss = '{0:.2f}'.format(min(hist.history['val_loss']))
        new_filepath = ds_name + '-' + m_name + '-valloss' + str(val_loss)
        os.rename(filepath, new_filepath)

print(results)

#try using this ami: vict0rsch-1.0

#git clone https://github.com/wroscoe/donkey.git
#git fetch origin wr/amazon_test
#git checkout wr/amazon_test

#virtualenv -p python3 env 
#source env/bin/activate

#pip install -e .
#pip install keras tensorflow-gpu scikit-image
#python demos/amazon_test.py

#install cudu: https://developer.nvidia.com/cuda-downloads
