"""
Keras model constructors.

All models accept 120x160x3 images and output a 
single floating point number (ie steering angle)  

"""

from keras.layers import Input, LSTM, Dense, merge
from keras.models import Model
from keras.models import Sequential
from keras.layers import Convolution2D, MaxPooling2D, SimpleRNN, Reshape, BatchNormalization
from keras.layers import Activation, Dropout, Flatten, Dense

def cnn3_full1():

    img_in = Input(shape=(120, 160, 3), name='img_in')
    angle_in = Input(shape=(1,), name='angle_in')

    x = Convolution2D(8, 3, 3)(img_in)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    x = Convolution2D(16, 3, 3)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    x = Convolution2D(32, 3, 3)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    merged = Flatten()(x)

    x = Dense(256)(merged)
    x = Activation('linear')(x)
    x = Dropout(.2)(x)

    angle_out = Dense(1, name='angle_out')(x)

    model = Model(input=[img_in], output=[angle_out])
    return model


def cnn3_full1_rnn1():

    img_in = Input(shape=(120, 160, 3), name='img_in')
    angle_in = Input(shape=(1,), name='angle_in')

    x = Convolution2D(8, 3, 3)(img_in)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    x = Convolution2D(16, 3, 3)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    x = Convolution2D(32, 3, 3)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    merged = Flatten()(x)

    x = Dense(256)(merged)
    x = Activation('relu')(x)
    x = Dropout(.2)(x)

    x = Reshape((1, 256))(x)
    x = SimpleRNN(256, activation='linear')(x)

    throttle_out = Dense(1, name='throttle_out')(x)
    angle_out = Dense(1, name='angle_out')(x)

    model = Model(input=[img_in], output=[angle_out])
    return model


def cnn1_full1():

    img_in = Input(shape=(120, 160, 3), name='img_in')
    angle_in = Input(shape=(1,), name='angle_in')
    
    x = Convolution2D(1, 3, 3)(img_in)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    merged = Flatten()(x)

    x = Dense(32)(merged)
    x = Activation('linear')(x)
    x = Dropout(.05)(x)

    angle_out = Dense(1, name='angle_out')(x)

    model = Model(input=[img_in], output=[angle_out])
    return model


def norm_cnn3_full1():

    img_in = Input(shape=(120, 160, 3), name='img_in')
    angle_in = Input(shape=(1,), name='angle_in')

    x = BatchNormalization()(img_in)
    x = Convolution2D(8, 3, 3)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    x = Convolution2D(16, 3, 3)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    x = Convolution2D(32, 3, 3)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D(pool_size=(2, 2))(x)

    merged = Flatten()(x)

    x = Dense(256)(merged)
    x = Activation('linear')(x)
    x = Dropout(.2)(x)

    angle_out = Dense(1, name='angle_out')(x)

    model = Model(input=[img_in], output=[angle_out])
    return model