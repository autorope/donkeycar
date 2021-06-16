"""

keras.py

Methods to create, use, save and load pilots. Pilots contain the highlevel
logic used to determine the angle and throttle of a vehicle. Pilots can
include one or more models to help direct the vehicles motion.

"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, Tuple, Optional, Union
import donkeycar as dk

from donkeycar.utils import normalize_image, linear_bin
from donkeycar.pipeline.types import TubRecord

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.layers import Convolution2D, MaxPooling2D, \
    BatchNormalization
from tensorflow.keras.layers import Activation, Dropout, Flatten
from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import TimeDistributed as TD
from tensorflow.keras.layers import Conv3D, MaxPooling3D, Conv2DTranspose
from tensorflow.keras.backend import concatenate
from tensorflow.keras.models import Model, Sequential
from tensorflow.python.keras.callbacks import EarlyStopping, ModelCheckpoint

ONE_BYTE_SCALE = 1.0 / 255.0

# type of x
XY = Union[float, np.ndarray, Tuple[float, ...], Tuple[np.ndarray, ...]]


class KerasPilot(ABC):
    """
    Base class for Keras models that will provide steering and throttle to
    guide a car.
    """
    def __init__(self) -> None:
        self.model: Optional[Model] = None
        self.optimizer = "adam"
        print(f'Created {self}')

    def load(self, model_path: str) -> None:
        print(f'Loading model {model_path}')
        self.model = keras.models.load_model(model_path, compile=False)

    def load_weights(self, model_path: str, by_name: bool = True) -> None:
        assert self.model, 'Model not set'
        self.model.load_weights(model_path, by_name=by_name)

    def shutdown(self) -> None:
        pass

    def compile(self) -> None:
        pass

    def set_optimizer(self, optimizer_type: str,
                      rate: float, decay: float) -> None:
        assert self.model, 'Model not set'
        if optimizer_type == "adam":
            self.model.optimizer = keras.optimizers.Adam(lr=rate, decay=decay)
        elif optimizer_type == "sgd":
            self.model.optimizer = keras.optimizers.SGD(lr=rate, decay=decay)
        elif optimizer_type == "rmsprop":
            self.model.optimizer = keras.optimizers.RMSprop(lr=rate, decay=decay)
        else:
            raise Exception("unknown optimizer type: %s" % optimizer_type)

    def get_input_shape(self) -> tf.TensorShape:
        assert self.model, 'Model not set'
        return self.model.inputs[0].shape

    def run(self, img_arr: np.ndarray, other_arr: np.ndarray = None) \
            -> Tuple[Union[float, np.ndarray], ...]:
        """
        Donkeycar parts interface to run the part in the loop.

        :param img_arr:     uint8 [0,255] numpy array with image data
        :param other_arr:   numpy array of additional data to be used in the
                            pilot, like IMU array for the IMU model or a
                            state vector in the Behavioural model
        :return:            tuple of (angle, throttle)
        """
        norm_arr = normalize_image(img_arr)
        return self.inference(norm_arr, other_arr)

    @abstractmethod
    def inference(self, img_arr: np.ndarray, other_arr: np.ndarray) \
            -> Tuple[Union[float, np.ndarray], ...]:
        """
        Virtual method to be implemented by child classes for inferencing

        :param img_arr:     float32 [0,1] numpy array with normalized image data
        :param other_arr:   numpy array of additional data to be used in the
                            pilot, like IMU array for the IMU model or a
                            state vector in the Behavioural model
        :return:            tuple of (angle, throttle)
        """
        pass

    def evaluate(self, record: TubRecord,
                 augmentation: 'ImageAugmentation' = None) \
            -> Tuple[Union[float, np.ndarray], ...]:
        # extract model input from record
        x0 = self.x_transform(record)
        x1 = x0[0] if isinstance(x0, tuple) else x0
        # apply augmentation to training data only
        x2 = augmentation.augment(x1) if augmentation else x1
        # normalise image, assume other input data comes already normalised
        x3 = normalize_image(x2)
        if isinstance(x0, tuple):
            return self.inference(x3, *x0[1:])
        else:
            return self.inference(x3, None)

    def train(self,
              model_path: str,
              train_data: 'BatchSequence',
              train_steps: int,
              batch_size: int,
              validation_data: 'BatchSequence',
              validation_steps: int,
              epochs: int,
              verbose: int = 1,
              min_delta: float = .0005,
              patience: int = 5,
              show_plot: bool = False) -> tf.keras.callbacks.History:
        """
        trains the model
        """
        model = self._get_train_model()
        self.compile()

        callbacks = [
            EarlyStopping(monitor='val_loss',
                          patience=patience,
                          min_delta=min_delta),
            ModelCheckpoint(monitor='val_loss',
                            filepath=model_path,
                            save_best_only=True,
                            verbose=verbose)]

        history: tf.keras.callbacks.History = model.fit(
            x=train_data,
            steps_per_epoch=train_steps,
            batch_size=batch_size,
            callbacks=callbacks,
            validation_data=validation_data,
            validation_steps=validation_steps,
            epochs=epochs,
            verbose=verbose,
            workers=1,
            use_multiprocessing=False
        )
            
        if show_plot:
            try:
                import matplotlib.pyplot as plt
                from pathlib import Path

                plt.figure(1)
                # Only do accuracy if we have that data
                # (e.g. categorical outputs)
                if 'angle_out_acc' in history.history:
                    plt.subplot(121)

                # summarize history for loss
                plt.plot(history.history['loss'])
                plt.plot(history.history['val_loss'])
                plt.title('model loss')
                plt.ylabel('loss')
                plt.xlabel('epoch')
                plt.legend(['train', 'validate'], loc='upper right')

                # summarize history for acc
                if 'angle_out_acc' in history.history:
                    plt.subplot(122)
                    plt.plot(history.history['angle_out_acc'])
                    plt.plot(history.history['val_angle_out_acc'])
                    plt.title('model angle accuracy')
                    plt.ylabel('acc')
                    plt.xlabel('epoch')

                plt.savefig(Path(model_path).with_suffix('.png'))
                # plt.show()

            except Exception as ex:
                print(f"problems with loss graph: {ex}")
            
        return history

    def _get_train_model(self) -> Model:
        """ Model used for training, could be just a sub part of the model"""
        return self.model

    def x_transform(self, record: TubRecord) -> XY:
        img_arr = record.image(cached=True)
        return img_arr

    def y_transform(self, record: TubRecord) -> XY:
        raise NotImplementedError(f'{self} not ready yet for new training '
                                  f'pipeline')

    def x_translate(self, x: XY) -> Dict[str, Union[float, np.ndarray]]:
        return {'img_in': x}

    def y_translate(self, y: XY) -> Dict[str, Union[float, np.ndarray]]:
        raise NotImplementedError(f'{self} not ready yet for new training '
                                  f'pipeline')

    def output_types(self) -> Tuple[Dict[str, np.typename], ...]:
        """ Used in tf.data, assume all types are doubles"""
        shapes = self.output_shapes()
        types = tuple({k: tf.float64 for k in d} for d in shapes)
        return types

    def output_shapes(self) -> Dict[str, tf.TensorShape]:
        return {}

    def __str__(self) -> str:
        """ For printing model initialisation """
        return type(self).__name__


class KerasCategorical(KerasPilot):
    """
    The KerasCategorical pilot breaks the steering and throttle decisions
    into discreet angles and then uses categorical cross entropy to train the
    network to activate a single neuron for each steering and throttle
    choice. This can be interesting because we get the confidence value as a
    distribution over all choices. This uses the dk.utils.linear_bin and
    dk.utils.linear_unbin to transform continuous real numbers into a range
    of discreet values for training and runtime. The input and output are
    therefore bounded and must be chosen wisely to match the data. The
    default ranges work for the default setup. But cars which go faster may
    want to enable a higher throttle range. And cars with larger steering
    throw may want more bins.
    """
    def __init__(self, input_shape=(120, 160, 3), throttle_range=0.5):
        super().__init__()
        self.model = default_categorical(input_shape)
        self.throttle_range = throttle_range

    def compile(self):
        self.model.compile(optimizer=self.optimizer, metrics=['accuracy'],
                           loss={'angle_out': 'categorical_crossentropy',
                                 'throttle_out': 'categorical_crossentropy'},
                           loss_weights={'angle_out': 0.5, 'throttle_out': 0.5})
        
    def inference(self, img_arr, other_arr):
        if img_arr is None:
            print('no image')
            return 0.0, 0.0

        img_arr = img_arr.reshape((1,) + img_arr.shape)
        angle_binned_tensor, throttle_binned_tensor = self.model(img_arr)
        angle_binned = angle_binned_tensor.numpy()
        throttle_binned = throttle_binned_tensor.numpy()
        N = len(throttle_binned[0])
        throttle = dk.utils.linear_unbin(throttle_binned, N=N,
                                         offset=0.0, R=self.throttle_range)
        angle = dk.utils.linear_unbin(angle_binned)
        return angle, throttle

    def y_transform(self, record: TubRecord):
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        angle = linear_bin(angle, N=15, offset=1, R=2.0)
        throttle = linear_bin(throttle, N=20, offset=0.0, R=self.throttle_range)
        return angle, throttle

    def y_translate(self, y: XY) -> Dict[str, Union[float, np.ndarray]]:
        if isinstance(y, tuple):
            angle, throttle = y
            return {'angle_out': angle, 'throttle_out': throttle}
        else:
            raise TypeError('Expected tuple')

    def output_shapes(self):
        # need to cut off None from [None, 120, 160, 3] tensor shape
        img_shape = self.get_input_shape()[1:]
        shapes = ({'img_in': tf.TensorShape(img_shape)},
                  {'angle_out': tf.TensorShape([15]),
                   'throttle_out': tf.TensorShape([20])})
        return shapes


class KerasLinear(KerasPilot):
    """
    The KerasLinear pilot uses one neuron to output a continous value via the
    Keras Dense layer with linear activation. One each for steering and
    throttle. The output is not bounded.
    """
    def __init__(self, num_outputs=2, input_shape=(120, 160, 3)):
        super().__init__()
        self.model = default_n_linear(num_outputs, input_shape)

    def compile(self):
        self.model.compile(optimizer=self.optimizer, loss='mse')

    def inference(self, img_arr, other_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        outputs = self.model(img_arr)
        steering = outputs[0].numpy()
        throttle = outputs[1].numpy()
        return steering[0][0], throttle[0][0]

    def y_transform(self, record: TubRecord):
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        return angle, throttle

    def y_translate(self, y: XY) -> Dict[str, Union[float, np.ndarray]]:
        if isinstance(y, tuple):
            angle, throttle = y
            return {'n_outputs0': angle, 'n_outputs1': throttle}
        else:
            raise TypeError('Expected tuple')

    def output_shapes(self):
        # need to cut off None from [None, 120, 160, 3] tensor shape
        img_shape = self.get_input_shape()[1:]
        shapes = ({'img_in': tf.TensorShape(img_shape)},
                  {'n_outputs0': tf.TensorShape([]),
                   'n_outputs1': tf.TensorShape([])})
        return shapes


class KerasInferred(KerasPilot):
    def __init__(self, num_outputs=1, input_shape=(120, 160, 3)):
        super().__init__()
        self.model = default_n_linear(num_outputs, input_shape)

    def compile(self):
        self.model.compile(optimizer=self.optimizer, loss='mse')

    def inference(self, img_arr, other_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        outputs = self.model(img_arr)
        steering = outputs[0].numpy()
        return steering[0], dk.utils.throttle(steering[0])

    def y_transform(self, record: TubRecord):
        angle: float = record.underlying['user/angle']
        return angle

    def y_translate(self, y: XY) -> Dict[str, Union[float, np.ndarray]]:
        return {'n_outputs0': y}

    def output_shapes(self):
        # need to cut off None from [None, 120, 160, 3] tensor shape
        img_shape = self.get_input_shape()[1:]
        shapes = ({'img_in': tf.TensorShape(img_shape)},
                  {'n_outputs0': tf.TensorShape([])})
        return shapes


class KerasIMU(KerasPilot):
    """
    A Keras part that take an image and IMU vector as input,
    outputs steering and throttle

    Note: When training, you will need to vectorize the input from the IMU.
    Depending on the names you use for imu records, something like this will
    work:

    X_keys = ['cam/image_array','imu_array']
    y_keys = ['user/angle', 'user/throttle']

    def rt(rec):
        rec['imu_array'] = np.array([ rec['imu/acl_x'], rec['imu/acl_y'],
        rec['imu/acl_z'],
            rec['imu/gyr_x'], rec['imu/gyr_y'], rec['imu/gyr_z'] ])
        return rec

    kl = KerasIMU()

    tubgroup = TubGroup(tub_names)
    train_gen, val_gen = tubgroup.get_train_val_gen(X_keys, y_keys,
                                                    record_transform=rt,
                                                    batch_size=cfg.BATCH_SIZE,
                                                    train_frac=cfg.TRAIN_TEST_SPLIT)

    """
    def __init__(self, num_outputs=2, num_imu_inputs=6, input_shape=(120, 160, 3)):
        super().__init__()
        self.num_imu_inputs = num_imu_inputs
        self.model = default_imu(num_outputs=num_outputs,
                                 num_imu_inputs=num_imu_inputs,
                                 input_shape=input_shape)

    def compile(self):
        self.model.compile(optimizer=self.optimizer, loss='mse')
        
    def inference(self, img_arr, other_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        imu_arr = np.array(other_arr).reshape(1, self.num_imu_inputs)
        outputs = self.model([img_arr, imu_arr])
        steering = outputs[0].numpy()
        throttle = outputs[1].numpy()
        return steering[0][0], throttle[0][0]

    def y_transform(self, record: TubRecord):
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        return {'n_out0': angle, 'n_out1': throttle}


class KerasBehavioral(KerasPilot):
    """
    A Keras part that take an image and Behavior vector as input,
    outputs steering and throttle
    """
    def __init__(self, num_behavior_inputs=2, input_shape=(120, 160, 3)):
        super(KerasBehavioral, self).__init__()
        self.model = default_bhv(num_bvh_inputs=num_behavior_inputs,
                                 input_shape=input_shape)

    def compile(self):
        self.model.compile(optimizer=self.optimizer, loss='mse')
        
    def inference(self, img_arr, state_array):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        bhv_arr = np.array(state_array).reshape(1, len(state_array))
        angle_binned_tensor, throttle_tensor = self.model([img_arr, bhv_arr])
        angle_binned = angle_binned_tensor.numpy()
        throttle = throttle_tensor.numpy()
        # In order to support older models with linear throttle,we will test for
        # shape of throttle to see if it's the newer binned version.
        N = len(throttle[0])
        
        if N > 0:
            throttle = dk.utils.linear_unbin(throttle, N=N, offset=0.0, R=0.5)
        else:
            throttle = throttle[0][0]
        angle_unbinned = dk.utils.linear_unbin(angle_binned)
        return angle_unbinned, throttle

    def y_transform(self, record: TubRecord):
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        angle = linear_bin(angle, N=15, offset=1, R=2.0)
        throttle = linear_bin(throttle, N=20, offset=0.0, R=0.5)
        return {'angle_out': angle, 'throttle_out': throttle}


class KerasLocalizer(KerasPilot):
    """
    A Keras part that take an image as input,
    outputs steering and throttle, and localisation category
    """
    def __init__(self, num_locations=8, input_shape=(120, 160, 3)):
        super().__init__()
        self.model = default_loc(num_locations=num_locations,
                                 input_shape=input_shape)

    def compile(self):
        self.model.compile(optimizer=self.optimizer, metrics=['acc'],
                           loss='mse')
        
    def inference(self, img_arr, other_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        angle_t, throttle_t, track_loc_t = self.model([img_arr])
        angle = angle_t.numpy()
        throttle = throttle_t.numpy()
        track_loc = track_loc_t.numpy()
        loc = np.argmax(track_loc[0])
        return angle, throttle, loc



def conv2d(filters, kernel, strides, layer_num, activation='relu'):
    """
    Helper function to create a standard valid-padded convolutional layer
    with square kernel and strides and unified naming convention

    :param filters:     channel dimension of the layer
    :param kernel:      creates (kernel, kernel) kernel matrix dimension
    :param strides:     creates (strides, strides) stride
    :param layer_num:   used in labelling the layer
    :param activation:  activation, defaults to relu
    :return:            tf.keras Convolution2D layer
    """
    return Convolution2D(filters=filters,
                         kernel_size=(kernel, kernel),
                         strides=(strides, strides),
                         activation=activation,
                         name='conv2d_' + str(layer_num))


def core_cnn_layers(img_in, drop, l4_stride=1):
    """
    Returns the core CNN layers that are shared among the different models,
    like linear, imu, behavioural

    :param img_in:          input layer of network
    :param drop:            dropout rate
    :param l4_stride:       4-th layer stride, default 1
    :return:                stack of CNN layers
    """
    x = img_in
    x = conv2d(24, 5, 2, 1)(x)
    x = Dropout(drop)(x)
    x = conv2d(32, 5, 2, 2)(x)
    x = Dropout(drop)(x)
    x = conv2d(64, 5, 2, 3)(x)
    x = Dropout(drop)(x)
    x = conv2d(64, 3, l4_stride, 4)(x)
    x = Dropout(drop)(x)
    x = conv2d(64, 3, 1, 5)(x)
    x = Dropout(drop)(x)
    x = Flatten(name='flattened')(x)
    return x


def default_n_linear(num_outputs, input_shape=(120, 160, 3)):
    drop = 0.2
    img_in = Input(shape=input_shape, name='img_in')
    x = core_cnn_layers(img_in, drop)
    x = Dense(100, activation='relu', name='dense_1')(x)
    x = Dropout(drop)(x)
    x = Dense(50, activation='relu', name='dense_2')(x)
    x = Dropout(drop)(x)

    outputs = []
    for i in range(num_outputs):
        outputs.append(
            Dense(1, activation='linear', name='n_outputs' + str(i))(x))

    model = Model(inputs=[img_in], outputs=outputs)
    return model


def default_categorical(input_shape=(120, 160, 3)):
    drop = 0.2
    img_in = Input(shape=input_shape, name='img_in')
    x = core_cnn_layers(img_in, drop, l4_stride=2)
    x = Dense(100, activation='relu', name="dense_1")(x)
    x = Dropout(drop)(x)
    x = Dense(50, activation='relu', name="dense_2")(x)
    x = Dropout(drop)(x)
    # Categorical output of the angle into 15 bins
    angle_out = Dense(15, activation='softmax', name='angle_out')(x)
    # categorical output of throttle into 20 bins
    throttle_out = Dense(20, activation='softmax', name='throttle_out')(x)

    model = Model(inputs=[img_in], outputs=[angle_out, throttle_out])
    return model


def default_imu(num_outputs, num_imu_inputs, input_shape):
    drop = 0.2
    img_in = Input(shape=input_shape, name='img_in')
    imu_in = Input(shape=(num_imu_inputs,), name="imu_in")

    x = core_cnn_layers(img_in, drop)
    x = Dense(100, activation='relu')(x)
    x = Dropout(.1)(x)
    
    y = imu_in
    y = Dense(14, activation='relu')(y)
    y = Dense(14, activation='relu')(y)
    y = Dense(14, activation='relu')(y)
    
    z = concatenate([x, y])
    z = Dense(50, activation='relu')(z)
    z = Dropout(.1)(z)
    z = Dense(50, activation='relu')(z)
    z = Dropout(.1)(z)

    outputs = []
    for i in range(num_outputs):
        outputs.append(Dense(1, activation='linear', name='out_' + str(i))(z))
        
    model = Model(inputs=[img_in, imu_in], outputs=outputs)
    return model


def default_bhv(num_bvh_inputs, input_shape):
    drop = 0.2
    img_in = Input(shape=input_shape, name='img_in')
    bvh_in = Input(shape=(num_bvh_inputs,), name="behavior_in")

    x = core_cnn_layers(img_in, drop)
    x = Dense(100, activation='relu')(x)
    x = Dropout(.1)(x)
    
    y = bvh_in
    y = Dense(num_bvh_inputs * 2, activation='relu')(y)
    y = Dense(num_bvh_inputs * 2, activation='relu')(y)
    y = Dense(num_bvh_inputs * 2, activation='relu')(y)
    
    z = concatenate([x, y])
    z = Dense(100, activation='relu')(z)
    z = Dropout(.1)(z)
    z = Dense(50, activation='relu')(z)
    z = Dropout(.1)(z)
    
    # Categorical output of the angle into 15 bins
    angle_out = Dense(15, activation='softmax', name='angle_out')(z)
    # Categorical output of throttle into 20 bins
    throttle_out = Dense(20, activation='softmax', name='throttle_out')(z)
        
    model = Model(inputs=[img_in, bvh_in], outputs=[angle_out, throttle_out])
    return model


def default_loc(num_locations, input_shape):
    drop = 0.2
    img_in = Input(shape=input_shape, name='img_in')

    x = core_cnn_layers(img_in, drop)
    x = Dense(100, activation='relu')(x)
    x = Dropout(drop)(x)
    
    z = Dense(50, activation='relu')(x)
    z = Dropout(drop)(z)

    # linear output of the angle
    angle_out = Dense(1, activation='linear', name='angle')(z)
    # linear output of throttle
    throttle_out = Dense(1, activation='linear', name='throttle')(z)
    # categorical output of location
    loc_out = Dense(num_locations, activation='softmax', name='loc')(z)

    model = Model(inputs=[img_in], outputs=[angle_out, throttle_out, loc_out])
    return model


class KerasRNN_LSTM(KerasPilot):
    def __init__(self, input_shape=(120, 160, 3), seq_length=3, num_outputs=2):
        super().__init__()
        self.input_shape = input_shape
        self.model = rnn_lstm(seq_length=seq_length,
                              num_outputs=num_outputs,
                              input_shape=input_shape)
        self.seq_length = seq_length
        self.img_seq = []
        self.optimizer = "rmsprop"

    def compile(self):
        self.model.compile(optimizer=self.optimizer, loss='mse')

    def inference(self, img_arr, other_arr):
        if img_arr.shape[2] == 3 and self.input_shape[2] == 1:
            img_arr = dk.utils.rgb2gray(img_arr)

        while len(self.img_seq) < self.seq_length:
            self.img_seq.append(img_arr)

        self.img_seq = self.img_seq[1:]
        self.img_seq.append(img_arr)
        
        img_arr = np.array(self.img_seq).reshape((1, self.seq_length,
                                                  *self.input_shape))
        outputs = self.model([img_arr])
        steering = outputs[0][0].numpy()
        throttle = outputs[0][1].numpy()
        return steering, throttle


def rnn_lstm(seq_length=3, num_outputs=2, input_shape=(120, 160, 3)):
    # add sequence length dimensions as keras time-distributed expects shape
    # of (num_samples, seq_length, input_shape)
    img_seq_shape = (seq_length,) + input_shape   
    img_in = Input(batch_shape=img_seq_shape, name='img_in')
    drop_out = 0.3

    x = Sequential()
    x.add(TD(Convolution2D(24, (5,5), strides=(2,2), activation='relu'),
             input_shape=img_seq_shape))
    x.add(TD(Dropout(drop_out)))
    x.add(TD(Convolution2D(32, (5, 5), strides=(2, 2), activation='relu')))
    x.add(TD(Dropout(drop_out)))
    x.add(TD(Convolution2D(32, (3, 3), strides=(2, 2), activation='relu')))
    x.add(TD(Dropout(drop_out)))
    x.add(TD(Convolution2D(32, (3, 3), strides=(1, 1), activation='relu')))
    x.add(TD(Dropout(drop_out)))
    x.add(TD(MaxPooling2D(pool_size=(2, 2))))
    x.add(TD(Flatten(name='flattened')))
    x.add(TD(Dense(100, activation='relu')))
    x.add(TD(Dropout(drop_out)))
      
    x.add(LSTM(128, return_sequences=True, name="LSTM_seq"))
    x.add(Dropout(.1))
    x.add(LSTM(128, return_sequences=False, name="LSTM_fin"))
    x.add(Dropout(.1))
    x.add(Dense(128, activation='relu'))
    x.add(Dropout(.1))
    x.add(Dense(64, activation='relu'))
    x.add(Dense(10, activation='relu'))
    x.add(Dense(num_outputs, activation='linear', name='model_outputs'))
    return x


class Keras3D_CNN(KerasPilot):
    def __init__(self, input_shape=(120, 160, 3), seq_length=20, num_outputs=2):
        super().__init__()
        self.input_shape = input_shape
        self.model = build_3d_cnn(input_shape, s=seq_length,
                                  num_outputs=num_outputs)
        self.seq_length = seq_length
        self.img_seq = []

    def compile(self):
        self.model.compile(loss='mean_squared_error',
                           optimizer=self.optimizer,
                           metrics=['accuracy'])

    def inference(self, img_arr, other_arr):

        if img_arr.shape[2] == 3 and self.input_shape[2] == 1:
            img_arr = dk.utils.rgb2gray(img_arr)

        while len(self.img_seq) < self.seq_length:
            self.img_seq.append(img_arr)

        self.img_seq = self.img_seq[1:]
        self.img_seq.append(img_arr)
        
        img_arr = np.array(self.img_seq).reshape((1, self.seq_length,
                                                  *self.input_shape))
        outputs = self.model([img_arr])
        steering = outputs[0][0].numpy()
        throttle = outputs[0][1].numpy()
        return steering, throttle


def build_3d_cnn(input_shape, s, num_outputs):
    """
    Credit: https://github.com/jessecha/DNRacing/blob/master/3D_CNN_Model/model.py

    :param input_shape:     image input shape
    :param s:               sequence length
    :param num_outputs:     output dimension
    :return:
    """
    input_shape = (s, ) + input_shape
    model = Sequential()

    # Second layer
    model.add(Conv3D(
        filters=16, kernel_size=(3, 3, 3), strides=(1, 3, 3),
        data_format='channels_last', padding='same', input_shape=input_shape)
    )
    model.add(Activation('relu'))
    model.add(MaxPooling3D(
        pool_size=(1, 2, 2), strides=(1, 2, 2), padding='valid',
        data_format=None)
    )
    # Third layer
    model.add(Conv3D(
        filters=32, kernel_size=(3, 3, 3), strides=(1, 1, 1),
        data_format='channels_last', padding='same')
    )
    model.add(Activation('relu'))
    model.add(MaxPooling3D(
        pool_size=(1, 2, 2), strides=(1, 2, 2), padding='valid',
        data_format=None)
    )
    # Fourth layer
    model.add(Conv3D(
        filters=64, kernel_size=(3, 3, 3), strides=(1, 1, 1),
        data_format='channels_last', padding='same')
    )
    model.add(Activation('relu'))
    model.add(MaxPooling3D(
        pool_size=(1, 2, 2), strides=(1, 2, 2), padding='valid',
        data_format=None)
    )
    # Fifth layer
    model.add(Conv3D(
        filters=128, kernel_size=(3, 3, 3), strides=(1, 1, 1),
        data_format='channels_last', padding='same')
    )
    model.add(Activation('relu'))
    model.add(MaxPooling3D(
        pool_size=(1, 2, 2), strides=(1, 2, 2), padding='valid',
        data_format=None)
    )
    # Fully connected layer
    model.add(Flatten())

    model.add(Dense(256))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(Dropout(0.5))

    model.add(Dense(256))
    model.add(BatchNormalization())
    model.add(Activation('relu'))
    model.add(Dropout(0.5))

    model.add(Dense(num_outputs))
    return model


class KerasLatent(KerasPilot):
    def __init__(self, num_outputs=2, input_shape=(120, 160, 3)):
        super().__init__()
        self.model = default_latent(num_outputs, input_shape)

    def compile(self):
        loss = {"img_out": "mse", "n_outputs0": "mse", "n_outputs1": "mse"}
        weights = {"img_out": 100.0, "n_outputs0": 2.0, "n_outputs1": 1.0}
        self.model.compile(optimizer=self.optimizer,
                           loss=loss, loss_weights=weights)

    def inference(self, img_arr, other_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        outputs = self.model(img_arr)
        steering = outputs[1].numpy()
        throttle = outputs[2].numpy()
        return steering[0][0], throttle[0][0]


def default_latent(num_outputs, input_shape):
    # TODO: this auto-encoder should run the standard cnn in encoding and
    #  have corresponding decoder. Also outputs should be reversed with
    #  images at end.
    drop = 0.2
    img_in = Input(shape=input_shape, name='img_in')
    x = img_in
    x = Convolution2D(24, (5,5), strides=(2,2), activation='relu', name="conv2d_1")(x)
    x = Dropout(drop)(x)
    x = Convolution2D(32, (5,5), strides=(2,2), activation='relu', name="conv2d_2")(x)
    x = Dropout(drop)(x)
    x = Convolution2D(32, (5,5), strides=(2,2), activation='relu', name="conv2d_3")(x)
    x = Dropout(drop)(x)
    x = Convolution2D(32, (3,3), strides=(1,1), activation='relu', name="conv2d_4")(x)
    x = Dropout(drop)(x)
    x = Convolution2D(32, (3,3), strides=(1,1), activation='relu', name="conv2d_5")(x)
    x = Dropout(drop)(x)
    x = Convolution2D(64, (3,3), strides=(2,2), activation='relu', name="conv2d_6")(x)
    x = Dropout(drop)(x)
    x = Convolution2D(64, (3,3), strides=(2,2), activation='relu', name="conv2d_7")(x)
    x = Dropout(drop)(x)
    x = Convolution2D(64, (1,1), strides=(2,2), activation='relu', name="latent")(x)
    
    y = Conv2DTranspose(filters=64, kernel_size=(3,3), strides=2, name="deconv2d_1")(x)
    y = Conv2DTranspose(filters=64, kernel_size=(3,3), strides=2, name="deconv2d_2")(y)
    y = Conv2DTranspose(filters=32, kernel_size=(3,3), strides=2, name="deconv2d_3")(y)
    y = Conv2DTranspose(filters=32, kernel_size=(3,3), strides=2, name="deconv2d_4")(y)
    y = Conv2DTranspose(filters=32, kernel_size=(3,3), strides=2, name="deconv2d_5")(y)
    y = Conv2DTranspose(filters=1, kernel_size=(3,3), strides=2, name="img_out")(y)
    
    x = Flatten(name='flattened')(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(drop)(x)
    x = Dense(100, activation='relu')(x)
    x = Dropout(drop)(x)
    x = Dense(50, activation='relu')(x)
    x = Dropout(drop)(x)

    outputs = [y]
    for i in range(num_outputs):
        outputs.append(Dense(1, activation='linear', name='n_outputs' + str(i))(x))
        
    model = Model(inputs=[img_in], outputs=outputs)
    return model
