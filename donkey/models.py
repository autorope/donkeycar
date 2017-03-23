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



def conv_layer_factory(x, filters=None, kernal=None, strides=None, activation='relu'):
    x = Convolution2D(filters, kernal, strides=strides, 
                      activation=activation)(x)
    #x = MaxPooling2D(pool_size=(2, 2))(x)
    return x

def dense_layer_factory(x, units=None, dropout=None, activation='relu'):
    x = Dense(units, activation=activation)(x)
    x = Dropout(dropout)(x)
    return x


def categorical_model_factory(conv=None, dense=None):

    img_in = Input(shape=(120, 160,3), name='img_in')

    x = img_in
    
    #create 
    for c in conv:
        x = conv_layer_factory(x, **c)
        
    x = Flatten()(x)
    
    for d in dense:
        x = dense_layer_factory(x, **d)
    
    angle_out = Dense(15, activation='softmax', name='angle_out')(x)
    
    throttle_out = Dense(1, activation='linear', name='throttle_out')(x)
    
    model = Model(inputs=[img_in], outputs=[angle_out, throttle_out])

    model.compile(optimizer='rmsprop',
                  loss={'angle_out': 'categorical_crossentropy', 'throttle_out': 'mean_squared_error'},
                  loss_weights={'angle_out': 1., 'throttle_out': .3})
    
    return model


## Model Architectures

nvidia_conv = [{'filters': 24, 'kernal': (5,5), 'strides':(2,2)}, 
        {'filters': 32, 'kernal': (5,5), 'strides':(2,2)},
        {'filters': 64, 'kernal': (5,5), 'strides':(2,2)},
        {'filters': 64, 'kernal': (3,3), 'strides':(2,2)},
        {'filters': 64, 'kernal': (3,3), 'strides':(1,1)}]

nvidia_dense = [{'units': 100, 'dropout': .1}, 
        {'units': 50, 'dropout': .1}]

nvidia_arch = {'conv': nvidia_conv, 'dense':nvidia_dense}



def train_gen(model, model_path, train_gen, val_gen, n=10):

    #checkpoint to save model after each epoch
    save_best = keras.callbacks.ModelCheckpoint(model_path, monitor='val_loss', verbose=1, 
                                          save_best_only=False, mode='min')

    #stop training if the validation error stops improving.
    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=.0005, patience=4, 
                                         verbose=1, mode='auto')

    callbacks_list = [save_best, early_stop]


    hist = model.fit_generator(
                            train_gen, 
                            steps_per_epoch=n, 
                            nb_epoch=100, 
                            verbose=1, 
                            callbacks=callbacks_list, 
                            validation_data=val_gen, 
                            nb_val_samples=n*.2)