"""
Keras model constructors.

All models accept 120x160x3 images and output a
single floating point number (ie steering angle)

"""
import keras
from keras.layers import Input, Dense, merge
from keras.models import Model
from keras.models import Sequential
from keras.layers import Convolution2D, MaxPooling2D, SimpleRNN, Reshape, BatchNormalization
from keras.layers import Activation, Dropout, Flatten, Dense
from keras.regularizers import l2






def conv_factory(x, filters, kernal, strides):
    x = Convolution2D(filters, kernal, strides=strides, 
                      activation='relu')(x)
    #x = MaxPooling2D(pool_size=(2, 2))(x)
    return x

def dense_factory(x, neurons, dropout):
    x = Dense(neurons)(x)
    x = Activation('relu')(x)
    x = Dropout(dropout)(x)
    return x


def cnn3_full1_relu(conv, dense, dropout):

    img_in = Input(shape=(120, 160,3), name='img_in')

    x = img_in
    
    #create 
    for c in conv:
        x = conv_factory(x, c[0], c[1], c[2])
        
    x = Flatten()(x)
    
    for d in dense:
        x = dense_factory(x, d, dropout)
    
    angle_out = Dense(1, name='angle_out')(x)

    model = Model(inputs=[img_in], outputs=[angle_out])
    
    model.compile(optimizer='adam', loss='mean_squared_error')

    return model


def conv_dense_sigmoid(conv, dense, dropout):

    img_in = Input(shape=(120, 160,3), name='img_in')

    x = img_in
    
    #create 
    for c in conv:
        x = conv_factory(x, c[0], c[1], c[2])
        
    x = Flatten()(x)
    
    for d in dense:
        x = dense_factory(x, d, dropout)
    
    x = Dense(15)(x)
    angle_out = Activation('softmax')(x)

    model = Model(inputs=[img_in], outputs=[angle_out])
    model.compile(loss='categorical_crossentropy',
                  optimizer='rmsprop')
    return model