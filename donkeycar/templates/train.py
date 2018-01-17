#!/usr/bin/env python3
"""
Scripts to train a keras model using tensorflow.
Uses the data written by the donkey v2.2 tub writer,
but faster training with proper sampling of distribution over tubs. 
Has settings for continuous training that will look for new files as it trains. 
Modify send_model_to_pi is you wish continuous training to update your pi as it builds.
You can drop this in your ~/d2 dir.
Basic usage should feel familiar: python train.py --model models/mypilot
You might need to do a: pip install scikit-learn


Usage:
    train.py [--tub=<tub1,tub2,..tubn>] (--model=<model>) [--transfer=<model>] [--type=(linear|categorical|rnn|imu|behavior|3d)] [--continuous]

Options:
    -h --help     Show this screen.    
"""
import os
import glob
import random
import json
from threading import Lock

from docopt import docopt
import numpy as np
import keras

import donkeycar as dk
from donkeycar.parts.datastore import Tub
from donkeycar.parts.keras import KerasLinear, KerasIMU,\
     KerasCategorical, KerasBehavioral, Keras3D_CNN,\
     KerasRNN_LSTM
from donkeycar.utils import *

import sklearn
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
from PIL import Image

'''
matplotlib can be a pain to setup. So handle the case where it is absent. When present,
use it to generate a plot of training results.
'''
try:
    import matplotlib.pyplot as plt
    do_plot = True
except:
    do_plot = False
    
deterministic = False
use_early_stop = True
early_stop_patience = 5
min_delta = .0005

if deterministic:
    import tensorflow as tf
    import random as rn

    # The below is necessary in Python 3.2.3 onwards to
    # have reproducible behavior for certain hash-based operations.
    # See these references for further details:
    # https://docs.python.org/3.4/using/cmdline.html#envvar-PYTHONHASHSEED
    # https://github.com/fchollet/keras/issues/2280#issuecomment-306959926

    os.environ['PYTHONHASHSEED'] = '0'

    # The below is necessary for starting Numpy generated random numbers
    # in a well-defined initial state.

    np.random.seed(42)

    # The below is necessary for starting core Python generated random numbers
    # in a well-defined state.

    rn.seed(12345)

    # Force TensorFlow to use single thread.
    # Multiple threads are a potential source of
    # non-reproducible results.
    # For further details, see: https://stackoverflow.com/questions/42022950/which-seeds-have-to-be-set-where-to-realize-100-reproducibility-of-training-res

    session_conf = tf.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)

    from keras import backend as K

    # The below tf.set_random_seed() will make random number generation
    # in the TensorFlow backend have a well-defined initial state.
    # For further details, see: https://www.tensorflow.org/api_docs/python/tf/set_random_seed

    tf.set_random_seed(1234)

    sess = tf.Session(graph=tf.get_default_graph(), config=session_conf)
    K.set_session(sess)


'''
Tub management
'''
def make_key(sample):
    tub_path = sample['tub_path']
    index = sample['index']
    return tub_path + str(index)

def make_next_key(sample, index_offset):
    tub_path = sample['tub_path']
    index = sample['index'] + index_offset
    return tub_path + str(index)


def collate_records(records, gen_records, opts):

    for record_path in records:

        basepath = os.path.dirname(record_path)        
        index = get_record_index(record_path)
        sample = { 'tub_path' : basepath, "index" : index }
             
        key = make_key(sample)

        if key in gen_records:
            continue

        with open(record_path, 'r') as fp:
            json_data = json.load(fp)

        image_filename = json_data["cam/image_array"]
        image_path = os.path.join(basepath, image_filename)

        sample['record_path'] = record_path
        sample["image_path"] = image_path
        sample["json_data"] = json_data        

        angle = float(json_data['user/angle'])
        throttle = float(json_data["user/throttle"])

        if opts['categorical']:
            angle = dk.utils.linear_bin(angle)
            throttle = dk.utils.linear_bin(throttle, N=20, offset=0, R=0.5)

        sample['angle'] = angle
        sample['throttle'] = throttle

        try:
            accl_x = float(json_data['imu/acl_x'])
            accl_y = float(json_data['imu/acl_y'])
            accl_z = float(json_data['imu/acl_z'])

            gyro_x = float(json_data['imu/gyr_x'])
            gyro_y = float(json_data['imu/gyr_y'])
            gyro_z = float(json_data['imu/gyr_z'])

            sample['imu_array'] = np.array([accl_x, accl_y, accl_z, gyro_x, gyro_y, gyro_z])
        except:
            pass

        try:
            behavior_arr = np.array(json_data['behavior/one_hot_state_array'])
            sample["behavior_arr"] = behavior_arr
        except:
            pass

        sample['img_data'] = None

        #now assign test or val
        sample['train'] = (random.uniform(0., 1.0) > 0.2)

        gen_records[key] = sample


class MyCPCallback(keras.callbacks.ModelCheckpoint):
    '''
    custom callback to interact with best val loss during continuous training
    '''

    def __init__(self, send_model_cb=None, *args, **kwargs):
        super(MyCPCallback, self).__init__(*args, **kwargs)
        self.reset_best_end_of_epoch = False
        self.send_model_cb = send_model_cb
        self.last_modified_time = None

    def reset_best(self):
        self.reset_best_end_of_epoch = True

    def on_epoch_end(self, epoch, logs=None):
        super(MyCPCallback, self).on_epoch_end(epoch, logs)

        if self.send_model_cb:
            '''
            check whether the file changed and send to the pi
            '''
            filepath = self.filepath.format(epoch=epoch, **logs)
            if os.path.exists(filepath):
                last_modified_time = os.path.getmtime(filepath)
                if self.last_modified_time is None or self.last_modified_time < last_modified_time:
                    self.last_modified_time = last_modified_time
                    self.send_model_cb(filepath)

        '''
        when reset best is set, we want to make sure to run an entire epoch
        before setting our new best on the new total records
        '''        
        if self.reset_best_end_of_epoch:
            self.reset_best_end_of_epoch = False
            self.best = np.Inf
        

def send_model_to_pi(model_filename):
    #print('sending model to the pi')
    #command = 'scp %s tkramer@pi.local:~/d2/models/contin_train.h5' % model_filename
    #res = os.system(command)
    #print("result:", res)
    pass

def train(cfg, tub_names, model_name, transfer_model, model_type, continuous):
    '''
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    ''' 

    verbose = True

    #when transfering models, should we freeze all but the last N layers?
    #freeze_weights = True
    #N_layers_to_train = 7

    if continuous:
        print("continuous training")
    
    gen_records = {}
    opts = {}

    opts['categorical'] = False

    input_shape = (cfg.IMAGE_H, cfg.IMAGE_W, cfg.IMAGE_DEPTH)

    if model_type is None:
        model_type = "categorical"

    if model_type == "imu":
        kl = KerasIMU(input_shape=input_shape)
    elif model_type == "behavior":
        kl = KerasBehavioral(input_shape=input_shape)
    elif model_type == "linear":
        kl = KerasLinear(num_outputs=2, input_shape=input_shape)
    elif model_type == "categorical":
        kl = KerasCategorical(input_shape=input_shape)
        opts['categorical'] = True
    else:
        raise Exception("unknown model type: %s" % model_type)

    print('training with model type', model_type)

    if transfer_model:
        print('loading weights from model', transfer_model)
        kl.load(transfer_model)

        '''
        if freeze_weights:
            num_to_freeze = len(kl.model.layers) - N_layers_to_train 
            print('freezing %d layers' % num_to_freeze)           
            for i in range(num_to_freeze):
                kl.model.layers[i].trainable = False
            kl.model.compile(optimizer='rmsprop', loss='mse')
        '''

        print(kl.model.summary())       

    opts['keras_pilot'] = kl
    opts['continuous'] = continuous

    records = gather_records(cfg, tub_names, opts)
    print('collating %d records ...' % (len(records)))
    collate_records(records, gen_records, opts)

    def generator(save_best, opts, data, batch_size, isTrainSet=True):
        
        num_records = len(data)

        while True:

            if isTrainSet and opts['continuous']:
                '''
                When continuous training, we look for new records after each epoch.
                This will add new records to the train and validation set.
                '''
                records = gather_records(cfg, tub_names, opts)
                if len(records) > num_records:
                    collate_records(records, gen_records, opts)
                    new_num_rec = len(data)
                    if new_num_rec > num_records:
                        print('picked up', new_num_rec - num_records, 'new records!')
                        num_records = new_num_rec 
                        save_best.reset_best()

            batch_data = []

            keys = list(data.keys())

            shuffle(keys)

            kl = opts['keras_pilot']

            if type(kl.model.output) is list:
                model_out_shape = (2, 1)
            else:
                model_out_shape = kl.model.output.shape

            if type(kl.model.input) is list:
                model_in_shape = (2, 1)
            else:    
                model_in_shape = kl.model.input.shape

            has_imu = type(kl) is KerasIMU
            has_bvh = type(kl) is KerasBehavioral

            for key in keys:

                if not key in data:
                    continue

                _record = data[key]

                if _record['train'] != isTrainSet:
                    continue

                batch_data.append(_record)

                if len(batch_data) == batch_size:
                    inputs_img = []
                    inputs_imu = []
                    inputs_bvh = []
                    angles = []
                    throttles = []

                    for record in batch_data:
                        #get image data if we don't already have it
                        if record['img_data'] is None:
                            img = Image.open(record['image_path'])
                            if img.height != cfg.IMAGE_H or img.width != cfg.IMAGE_W:
                                img = img.resize((cfg.IMAGE_H, cfg.IMAGE_W))
                            img_arr = np.array(img)
                            if img_arr.shape[2] == 3 and cfg.IMAGE_DEPTH == 1:
                                img_arr = dk.utils.rgb2gray(img_arr)
                            record['img_data'] = img_arr
                            
                        if has_imu:
                            inputs_imu.append(record['imu_array'])
                        
                        if has_bvh:
                            inputs_bvh.append(record['behavior_arr'])

                        inputs_img.append(record['img_data'])
                        angles.append(record['angle'])
                        throttles.append(record['throttle'])

                    img_arr = np.array(inputs_img).reshape(batch_size,\
                        cfg.IMAGE_H, cfg.IMAGE_W, cfg.IMAGE_DEPTH)

                    if has_imu:
                        X = [img_arr, np.array(inputs_imu)]
                    elif has_bvh:
                        X = [img_arr, np.array(inputs_bvh)]
                    else:
                        X = [img_arr]

                    if model_out_shape[1] == 2:
                        y = [np.array([angles, throttles])]
                    else:
                        y = [np.array(angles), np.array(throttles)]

                    yield X, y

                    batch_data = []


    model_path = os.path.expanduser(model_name)

    #checkpoint to save model after each epoch and send best to the pi.
    save_best = MyCPCallback(send_model_cb=send_model_to_pi,
                                    filepath=model_path,
                                    monitor='val_loss', 
                                    verbose=verbose, 
                                    save_best_only=True, 
                                    mode='min')

    #stop training if the validation error stops improving.
    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', 
                                                min_delta=min_delta, 
                                                patience=early_stop_patience, 
                                                verbose=verbose, 
                                                mode='auto')

    train_gen = generator(save_best, opts, gen_records, cfg.BATCH_SIZE, True)
    val_gen = generator(save_best, opts, gen_records, cfg.BATCH_SIZE, False)
 

    total_records = len(gen_records)

    num_train = 0
    num_val = 0

    for key, _record in gen_records.items():
        if _record['train'] == True:
            num_train += 1
        else:
            num_val += 1

    print("train: %d, val: %d" % (num_train, num_val))
    print('total records: %d' %(total_records))
    
    if not continuous:
        steps_per_epoch = num_train // cfg.BATCH_SIZE
    else:
        steps_per_epoch = 100
    
    val_steps = 10
    print('steps_per_epoch', steps_per_epoch)

    if continuous:
        epochs = 100000
    else:
        epochs = 200

    workers_count = 1
    use_multiprocessing = False

    callbacks_list = [save_best]

    if use_early_stop:
        callbacks_list.append(early_stop)
    
    history = kl.model.fit_generator(
                    train_gen, 
                    steps_per_epoch=steps_per_epoch, 
                    epochs=epochs, 
                    verbose=1, 
                    validation_data=val_gen,
                    callbacks=callbacks_list, 
                    validation_steps=val_steps,
                    workers=workers_count,
                    use_multiprocessing=use_multiprocessing)

    print("\n\n----------- Best Eval Loss :%f ---------" % save_best.best)

    try:
        if do_plot:
            # summarize history for loss
            plt.plot(history.history['loss'])
            plt.plot(history.history['val_loss'])
            plt.title('model loss : %f' % save_best.best)
            plt.ylabel('loss')
            plt.xlabel('epoch')
            plt.legend(['train', 'test'], loc='upper left')
            plt.savefig(model_path + '_loss_%f.png' % save_best.best)
            plt.show()
        else:
            print("not saving loss graph because matplotlib not set up.")
    except:
        print("problems with loss graph")


def sequence_train(cfg, tub_names, model_name, transfer_model, model_type, continuous):
    '''
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    trains models which take sequence of images
    '''
    import sklearn
    from sklearn.model_selection import train_test_split
    from sklearn.utils import shuffle
    from PIL import Image
    import json

    assert(not continuous)

    print("sequence of images training")

    if model_type == "rnn":
        kl = KerasRNN_LSTM(image_w=cfg.IMAGE_W,
            image_h=cfg.IMAGE_H,
            image_d=cfg.IMAGE_DEPTH,
            seq_length=cfg.SEQUENCE_LENGTH, num_outputs=2)

    elif model_type == "3d":
        kl = Keras3D_CNN(image_w=cfg.IMAGE_W,
            image_h=cfg.IMAGE_H,
            image_d=cfg.IMAGE_DEPTH,
            seq_length=cfg.SEQUENCE_LENGTH,
            num_outputs=2)
    else:
        raise Exception("unknown model type: %s" % model_type)

    tubs = gather_tubs(cfg, tub_names)

    records = []

    for tub in tubs:
        record_paths = glob.glob(os.path.join(tub.path, 'record_*.json'))
        print("Tub:", tub.path, "has", len(record_paths), 'records')

        record_paths.sort(key=get_record_index)
        records += record_paths


    print('collating records')
    gen_records = {}

    for record_path in records:

        with open(record_path, 'r') as fp:
            json_data = json.load(fp)

        basepath = os.path.dirname(record_path)
        image_filename = json_data["cam/image_array"]
        image_path = os.path.join(basepath, image_filename)
        sample = { 'record_path' : record_path, "image_path" : image_path, "json_data" : json_data }

        sample["tub_path"] = basepath
        sample["index"] = get_image_index(image_filename)

        angle = float(json_data['user/angle'])
        throttle = float(json_data["user/throttle"])

        sample['target_output'] = np.array([angle, throttle])

        sample['img_data'] = None

        key = make_key(sample)

        gen_records[key] = sample



    print('collating sequences')

    sequences = []

    for k, sample in gen_records.items():

        seq = []

        for i in range(cfg.SEQUENCE_LENGTH):
            key = make_next_key(sample, i)
            if key in gen_records:
                seq.append(gen_records[key])
            else:
                continue

        if len(seq) != cfg.SEQUENCE_LENGTH:
            continue

        sequences.append(seq)



    #shuffle and split the data
    train_data, val_data  = train_test_split(sequences, shuffle=True, test_size=(1 - cfg.TRAIN_TEST_SPLIT))


    def generator(data, batch_size=cfg.BATCH_SIZE):
        num_records = len(data)

        while True:
            #shuffle again for good measure
            shuffle(data)

            for offset in range(0, num_records, batch_size):
                batch_data = data[offset:offset+batch_size]

                if len(batch_data) != batch_size:
                    break

                b_inputs_img = []
                b_labels = []

                for seq in batch_data:
                    inputs_img = []
                    labels = []
                    for record in seq:
                        #get image data if we don't already have it
                        if record['img_data'] is None:
                            img_arr = np.array(Image.open(record['image_path']))
                            if img_arr.shape[2] == 3 and cfg.IMAGE_DEPTH == 1:
                                img_arr = dk.utils.rgb2gray(img_arr)
                            record['img_data'] = img_arr
                            
                        inputs_img.append(record['img_data'])
                    labels.append(seq[-1]['target_output'])

                    b_inputs_img.append(inputs_img)
                    b_labels.append(labels)

                X = [np.array(b_inputs_img).reshape(batch_size,\
                    cfg.SEQUENCE_LENGTH, cfg.IMAGE_H, cfg.IMAGE_W, cfg.IMAGE_DEPTH)]

                y = np.array(b_labels).reshape(batch_size, 2)

                yield X, y

    train_gen = generator(train_data)
    val_gen = generator(val_data)
    

    model_path = os.path.expanduser(model_name)

    total_records = len(sequences)
    total_train = len(train_data)
    total_val = len(val_data)

    print('train: %d, validation: %d' %(total_train, total_val))
    steps_per_epoch = total_train // cfg.BATCH_SIZE
    print('steps_per_epoch', steps_per_epoch)

    kl.train(train_gen, 
        val_gen, 
        saved_model_path=model_path,
        steps=steps_per_epoch,
        train_split=cfg.TRAIN_TEST_SPLIT,
        use_early_stop = False)



def multi_train(cfg, tub, model, transfer, model_type, continuous):
    '''
    choose the right regime for the given model type
    '''
    train_fn = train
    if model_type == "rnn" or model_type == '3d':
        train_fn = sequence_train

    train_fn(cfg, tub, model, transfer, model_type, continuous)
    
if __name__ == "__main__":
    args = docopt(__doc__)
    cfg = dk.load_config()
    tub = args['--tub']
    model = args['--model']
    transfer = args['--transfer']
    model_type = args['--type']
    continuous = args['--continuous']
    multi_train(cfg, tub, model, transfer, model_type, continuous)
    
