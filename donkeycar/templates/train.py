#!/usr/bin/env python3
"""
Scripts to train a keras model using tensorflow.
Uses the data written by the donkey v2.2 tub writer,
but faster training with proper sampling of distribution over tubs. 
Has settings for continuous training that will look for new files as it trains. 
Modify on_best_model if you wish continuous training to update your pi as it builds.
You can drop this in your ~/d2 dir.
Basic usage should feel familiar: python train.py --model models/mypilot
You might need to do a: pip install scikit-learn


Usage:
    train.py [--tub=<tub1,tub2,..tubn>] (--model=<model>) [--transfer=<model>] [--type=(linear|categorical|rnn|imu|behavior|3d)] [--continuous] [--aug]

Options:
    -h --help     Show this screen.    
"""
import os
import glob
import random
import json
from threading import Lock
import time

from docopt import docopt
import numpy as np
import keras

import donkeycar as dk
from donkeycar.parts.datastore import Tub
from donkeycar.parts.keras import KerasLinear, KerasIMU,\
     KerasCategorical, KerasBehavioral, Keras3D_CNN,\
     KerasRNN_LSTM
from donkeycar.parts.augment import augment_image
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

        try:
            with open(record_path, 'r') as fp:
                json_data = json.load(fp)
        except:
            continue

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


def save_json_and_weights(model, filename):
    '''
    given a keras model and a .h5 filename, save the model file
    in the json format and the weights file in the h5 format
    '''
    if not '.h5' == filename[-3:]:
        raise Exception("Model filename should end with .h5")

    arch = model.to_json()
    json_fnm = filename[:-2] + "json"
    weights_fnm = filename[:-2] + "weights"

    with open(json_fnm, "w") as outfile:
        parsed = json.loads(arch)
        arch_pretty = json.dumps(parsed, indent=4, sort_keys=True)
        outfile.write(arch_pretty)

    model.save_weights(weights_fnm)
    return json_fnm, weights_fnm


class MyCPCallback(keras.callbacks.ModelCheckpoint):
    '''
    custom callback to interact with best val loss during continuous training
    '''

    def __init__(self, send_model_cb=None, cfg=None, *args, **kwargs):
        super(MyCPCallback, self).__init__(*args, **kwargs)
        self.reset_best_end_of_epoch = False
        self.send_model_cb = send_model_cb
        self.last_modified_time = None
        self.cfg = cfg

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
                    self.send_model_cb(self.cfg, self.model, filepath)

        '''
        when reset best is set, we want to make sure to run an entire epoch
        before setting our new best on the new total records
        '''        
        if self.reset_best_end_of_epoch:
            self.reset_best_end_of_epoch = False
            self.best = np.Inf
        

def on_best_model(cfg, model, model_filename):
    #Save json and weights file too
    json_fnm, weights_fnm = save_json_and_weights(model, model_filename)

    if not cfg.SEND_BEST_MODEL_TO_PI:
        return

    on_windows = os.name == 'nt'

    #If we wish, send the best model to the pi.
    #On mac or linux we have scp:
    if not on_windows:
        print('sending model to the pi')
        
        command = 'scp %s %s@%s:~/%s/models/;' % (weights_fnm, cfg.PI_USERNAME, cfg.PI_HOSTNAME, cfg.PI_DONKEY_ROOT)
        command += 'scp %s %s@%s:~/%s/models/;' % (json_fnm, cfg.PI_USERNAME, cfg.PI_HOSTNAME, cfg.PI_DONKEY_ROOT)
        command += 'scp %s %s@%s:~/%s/models/;' % (model_filename, cfg.PI_USERNAME, cfg.PI_HOSTNAME, cfg.PI_DONKEY_ROOT)
    
        print("sending", command)
        res = os.system(command)
        print(res)

    else: #yes, we are on windows machine

    #On windoz no scp. In oder to use this you must first setup
    #an ftp daemon on the pi. ie. sudo apt-get install vsftpd
    #and then make sure you enable write permissions in the conf
        try:
            import paramiko
        except:
            raise Exception("first install paramiko: pip install paramiko")

        host = cfg.PI_HOSTNAME
        username = cfg.PI_USERNAME
        password = cfg.PI_PASSWD
        server = host
        files = []

        localpath = weights_fnm
        remotepath = '/home/%s/%s/%s' %(username, cfg.PI_DONKEY_ROOT, weights_fnm.replace('\\', '/'))
        files.append((localpath, remotepath))

        localpath = json_fnm
        remotepath = '/home/%s/%s/%s' %(username, cfg.PI_DONKEY_ROOT, json_fnm.replace('\\', '/'))
        files.append((localpath, remotepath))

        localpath = model_filename
        remotepath = '/home/%s/%s/%s' %(username, cfg.PI_DONKEY_ROOT, model_filename.replace('\\', '/'))
        files.append((localpath, remotepath))

        print("sending", files)

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
            ssh.connect(server, username=username, password=password)
            sftp = ssh.open_sftp()
        
            for localpath, remotepath in files:
                sftp.put(localpath, remotepath)

            sftp.close()
            ssh.close()
            print("send succeded")
        except:
            print("send failed")
    

def train(cfg, tub_names, model_name, transfer_model, model_type, continuous, aug):
    '''
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    ''' 

    verbose = cfg.VEBOSE_TRAIN

    
    if continuous:
        print("continuous training")
    
    gen_records = {}
    opts = {}

    kl = get_model_by_type(model_type, cfg=cfg)

    opts['categorical'] = type(kl) in [KerasCategorical, KerasBehavioral]

    print('training with model type', type(kl))

    if transfer_model:
        print('loading weights from model', transfer_model)
        kl.load(transfer_model)

        #when transfering models, should we freeze all but the last N layers?
        if cfg.FREEZE_LAYERS:
            num_to_freeze = len(kl.model.layers) - cfg.NUM_LAST_LAYERS_TO_TRAIN 
            print('freezing %d layers' % num_to_freeze)           
            for i in range(num_to_freeze):
                kl.model.layers[i].trainable = False        

    if cfg.OPTIMIZER:
        kl.set_optimizer(cfg.OPTIMIZER, cfg.LEARNING_RATE, cfg.LEARNING_RATE_DECAY)

    kl.compile()

    if cfg.PRINT_MODEL_SUMMARY:
        print(kl.model.summary())
    
    opts['keras_pilot'] = kl
    opts['continuous'] = continuous

    records = gather_records(cfg, tub_names, opts, verbose=True)
    print('collating %d records ...' % (len(records)))
    collate_records(records, gen_records, opts)

    def generator(save_best, opts, data, batch_size, isTrainSet=True, min_records_to_train=1000):
        
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
                if num_records < min_records_to_train:
                    print("not enough records to train. need %d, have %d. waiting..." % (min_records_to_train, num_records))
                    time.sleep(10)
                    continue

            batch_data = []

            keys = list(data.keys())

            keys = shuffle(keys)

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

                if continuous:
                    #in continuous mode we need to handle files getting deleted
                    filename = _record['image_path']
                    if not os.path.exists(filename):
                        data.pop(key, None)
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
                            filename = record['image_path']
                            
                            img_arr = load_scaled_image_arr(filename, cfg)

                            if img_arr is None:
                                break
                            
                            if aug:
                                img_arr = augment_image(img_arr)

                            if cfg.CACHE_IMAGES:
                                record['img_data'] = img_arr
                        else:
                            img_arr = record['img_data']
                            
                        if has_imu:
                            inputs_imu.append(record['imu_array'])
                        
                        if has_bvh:
                            inputs_bvh.append(record['behavior_arr'])

                        inputs_img.append(img_arr)
                        angles.append(record['angle'])
                        throttles.append(record['throttle'])

                    if img_arr is None:
                        continue

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
    save_best = MyCPCallback(send_model_cb=on_best_model,
                                    filepath=model_path,
                                    monitor='val_loss', 
                                    verbose=verbose, 
                                    save_best_only=True, 
                                    mode='min',
                                    cfg=cfg)

    #stop training if the validation error stops improving.
    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', 
                                                min_delta=cfg.MIN_DELTA, 
                                                patience=cfg.EARLY_STOP_PATIENCE, 
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

    if steps_per_epoch < 2:
        raise Exception("Too little data to train. Please record more records.")

    if continuous:
        epochs = 100000
    else:
        epochs = cfg.MAX_EPOCHS

    workers_count = 1
    use_multiprocessing = False

    callbacks_list = [save_best]

    if cfg.USE_EARLY_STOP and not continuous:
        callbacks_list.append(early_stop)
    
    history = kl.model.fit_generator(
                    train_gen, 
                    steps_per_epoch=steps_per_epoch, 
                    epochs=epochs, 
                    verbose=cfg.VEBOSE_TRAIN, 
                    validation_data=val_gen,
                    callbacks=callbacks_list, 
                    validation_steps=val_steps,
                    workers=workers_count,
                    use_multiprocessing=use_multiprocessing)

    print("\n\n----------- Best Eval Loss :%f ---------" % save_best.best)

    if cfg.SHOW_PLOT:
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


def sequence_train(cfg, tub_names, model_name, transfer_model, model_type, continuous, aug):
    '''
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    trains models which take sequence of images
    '''
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
            data = shuffle(data)

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
                            img_arr = load_scaled_image_arr(record['image_path'], cfg)
                            if img_arr is None:
                                break
                            if aug:
                                img_arr = augment_image(img_arr)
                            if cfg.CACHE_IMAGES:
                                record['img_data'] = img_arr
                        else:
                            img_arr = record['img_data']                            
                            
                        inputs_img.append(img_arr)
                    
                    if img_arr is None:
                        continue

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

    if steps_per_epoch < 2:
        raise Exception("Too little data to train. Please record more records.")

    kl.train(train_gen, 
        val_gen, 
        saved_model_path=model_path,
        steps=steps_per_epoch,
        train_split=cfg.TRAIN_TEST_SPLIT,
        use_early_stop = cfg.USE_EARLY_STOP)



def multi_train(cfg, tub, model, transfer, model_type, continuous, aug):
    '''
    choose the right regime for the given model type
    '''
    train_fn = train
    if model_type in ("rnn",'3d'):
        train_fn = sequence_train

    train_fn(cfg, tub, model, transfer, model_type, continuous, aug)
    
if __name__ == "__main__":
    args = docopt(__doc__)
    cfg = dk.load_config()
    tub = args['--tub']
    model = args['--model']
    transfer = args['--transfer']
    model_type = args['--type']
    continuous = args['--continuous']
    aug = args['--aug']
    multi_train(cfg, tub, model, transfer, model_type, continuous, aug)
    
