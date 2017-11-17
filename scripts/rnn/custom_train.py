import os
import glob
import numpy as np
import donkeycar as dk
from donkeycar.parts.simulation import SteeringServer
from keras_rnn import KerasRNN_LSTM
from donkeycar.parts.datastore import Tub

CAT = False

SEQ_LEN = 3


'''
Tub management
'''
def expand_path_masks(paths):
    '''
    take a list of paths and expand any wildcards
    returns a new list of paths fully expanded
    '''
    import glob
    expanded_paths = []
    for path in paths:
        if '*' in path or '?' in path:
            mask_paths = glob.glob(path)
            expanded_paths += mask_paths
        else:
            expanded_paths.append(path)

    return expanded_paths


def gather_tub_paths(cfg, tub_names=None):
    '''
    takes as input the configuration, and the comma seperated list of tub paths
    returns a list of Tub paths
    '''
    if tub_names:
        tub_paths = [os.path.expanduser(n) for n in tub_names.split(',')]
        return expand_path_masks(tub_paths)
    else:
        return [os.path.join(cfg.DATA_PATH, n) for n in os.listdir(cfg.DATA_PATH)]


def gather_tubs(cfg, tub_names):
    '''
    takes as input the configuration, and the comma seperated list of tub paths
    returns a list of Tub objects initialized to each path
    '''    
    tub_paths = gather_tub_paths(cfg, tub_names)
    tubs = [Tub(p) for p in tub_paths]

    return tubs


def get_image_index(fnm):
    sl = os.path.basename(fnm).split('_')
    return int(sl[0])

def get_record_index(fnm):
    sl = os.path.basename(fnm).split('_')
    return int(sl[1].split('.')[0])

def make_key(sample):
    tub_path = sample['tub_path']
    index = sample['index']
    return tub_path + str(index)

def make_next_key(sample, index_offset):
    tub_path = sample['tub_path']
    index = sample['index'] + index_offset
    return tub_path + str(index)



def custom_train(cfg, tub_names, model_name):
    '''
    use the specified data in tub_names to train an artifical neural network
    saves the output trained model as model_name
    '''
    import sklearn
    from sklearn.model_selection import train_test_split
    from sklearn.utils import shuffle
    from PIL import Image
    import json


    print("custom rnn training")

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

        '''
        accl_x = float(json_data['imu/acl_x'])
        accl_y = float(json_data['imu/acl_y'])
        accl_z = float(json_data['imu/acl_z'])

        gyro_x = float(json_data['imu/gyr_x'])
        gyro_y = float(json_data['imu/gyr_y'])
        gyro_z = float(json_data['imu/gyr_z'])

        sample['imu_array'] = np.array([accl_x, accl_y, accl_z, gyro_x, gyro_y, gyro_z])
        '''

        sample['img_data'] = None

        key = make_key(sample)

        gen_records[key] = sample



    print('collating sequences')

    sequences = []

    for k, sample in gen_records.items():

        seq = []

        for i in range(SEQ_LEN):
            key = make_next_key(sample, i)
            if key in gen_records:
                seq.append(gen_records[key])
            else:
                continue

        if len(seq) != SEQ_LEN:
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
                b_inputs_imu = []
                b_labels = []

                for seq in batch_data:
                    inputs_img = []
                    labels = []
                    for record in seq:
                        #get image data if we don't already have it
                        if record['img_data'] is None:
                            record['img_data'] = np.array(Image.open(record['image_path']))
                            
                        inputs_img.append(record['img_data'])
                    labels.append(seq[-1]['target_output'])

                    b_inputs_img.append(inputs_img)
                    b_labels.append(labels)

                #X = [np.array(b_inputs_img), np.array(b_inputs_imu)]
                X = [np.array(b_inputs_img)]
                y = np.array(b_labels).reshape(batch_size, 2)

                yield X, y

    train_gen = generator(train_data)
    val_gen = generator(val_data)

    kl = KerasRNN_LSTM(seq_length=SEQ_LEN, num_outputs=2)

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


class CSteeringServer(SteeringServer):

    def __init__(self, *args, **kwargs):
        super(CSteeringServer, self).__init__(*args, **kwargs)
        self.last_steering = 0.0
        self.alpha = 0.6

    def approach(self, old_val, new_val, alpha):
        return ((1.0 - alpha) * old_val) + (alpha * new_val)

    def steering_control(self, steering):
        new_steer = self.approach(self.last_steering, steering, self.alpha)
        self.last_steering = new_steer
        return new_steer

    #def throttle_control(self, last_steering, last_throttle, speed, nn_throttle):
    #    return nn_throttle * 2.0

def sim(cfg, model, top_speed=5.0):
    '''
    Start a websocket SocketIO server to talk to a donkey simulator
    '''
    import socketio
    import donkeycar as dk

    if cfg is None:
        print('no config')
        return

    kl = KerasRNN_LSTM(seq_length=SEQ_LEN, num_outputs=2)
    
    #can provide an optional image filter part
    img_stack = None

    #load keras model
    kl.load(model)  

    #start socket server framework
    sio = socketio.Server()

    top_speed = float(top_speed)

    #start sim server handler
    ss = CSteeringServer(sio, kpart=kl, top_speed=top_speed, image_part=img_stack)
            
    #register events and pass to server handlers

    @sio.on('telemetry')
    def telemetry(sid, data):
        ss.telemetry(sid, data)

    @sio.on('connect')
    def connect(sid, environ):
        ss.connect(sid, environ)

    ss.go(('0.0.0.0', 9090))
