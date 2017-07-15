"""
models.py

Functions to create and train Keras models plus a few common model Architectures.

"""
import keras
from keras.layers import Input, Dense, merge
from keras.models import Model
from keras.models import Sequential
from keras.layers import Convolution2D, MaxPooling2D, SimpleRNN, Reshape, BatchNormalization
from keras.layers import Activation, Dropout, Flatten, Dense
from keras.regularizers import l2



def conv_layer_factory(x, filters=None, kernal=None,
                          strides=None, pool=None,
                          activation='relu'):

    x = Convolution2D(filters, kernal, strides=strides,
                      activation=activation)(x)
    if pool is not None:
        x = MaxPooling2D(pool_size=pool)(x)
    return x


def dense_layer_factory(x, units=None, dropout=None, activation='relu'):
    x = Dense(units, activation=activation)(x)
    x = Dropout(dropout)(x)
    return x


def categorical_model_factory(conv=None, dense=None):
    '''
    Function to create models with convolutional heads and dense tails.
    Accepts dictionaries defining the conv and dense layers.
    '''

    img_in = Input(shape=(120, 160,3), name='img_in')

    x = img_in

    #create convolutional layers
    for c in conv:
        x = conv_layer_factory(x, **c)

    x = Flatten(name='flattened')(x)

    #create dense layers
    for d in dense:
        x = dense_layer_factory(x, **d)

    #categorical output of the angle
    angle_out = Dense(15, activation='softmax', name='angle_out')(x)

    #continous output of throttle
    throttle_out = Dense(1, activation='relu', name='throttle_out')(x)

    #continous output of speed
    speed_out = Dense(1, activation='relu', name='speed_out')(x)

    model = Model(inputs=[img_in], outputs=[angle_out, throttle_out, speed_out])

    #define loss function that weights angle loss more than throttle loss
    model.compile(optimizer='rmsprop',
                  loss={'angle_out': 'categorical_crossentropy', 'throttle_out': 'mean_absolute_error', 'speed_out': 'mean_absolute_error'},
                  loss_weights={'angle_out': 0.9, 'throttle_out': 0.1, 'speed_out': 0.1})

    model.summary()

    return model



########################
#                      #
#     Architectures    #
#                      #
########################



nvidia_conv = [{'filters': 24, 'kernal': (5,5), 'strides':(2,2)},
        {'filters': 32, 'kernal': (5,5), 'strides':(2,2)},
        {'filters': 64, 'kernal': (5,5), 'strides':(2,2)},
        {'filters': 64, 'kernal': (3,3), 'strides':(2,2)},
        {'filters': 64, 'kernal': (3,3), 'strides':(1,1)}]

nvidia_dense = [{'units': 100, 'dropout': .1},
        {'units': 50, 'dropout': .1}]

nvidia_arch = {'conv': nvidia_conv, 'dense':nvidia_dense}




def train_gen(model, model_path, train_gen, val_gen, steps=10, epochs=100, ):
    '''
    Function to train models and save their best models after each epoch.
    Return the hist object.
    '''


    #checkpoint to save model after each epoch
    save_best = keras.callbacks.ModelCheckpoint(model_path, monitor='val_loss', verbose=1,
                                          save_best_only=True, mode='min')

    #stop training if the validation error stops improving.
    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=.0005, patience=6,
                                         verbose=1, mode='auto')

    callbacks_list = [save_best, early_stop]


    hist = model.fit_generator(
                            train_gen,
                            steps_per_epoch=steps,
                            nb_epoch=epochs,
                            verbose=1,
                            callbacks=callbacks_list,
                            validation_data=val_gen,
                            nb_val_samples=steps*.2)

    return hist
