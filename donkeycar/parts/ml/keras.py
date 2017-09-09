'''

pilots.py

Methods to create, use, save and load pilots. Pilots 
contain the highlevel logic used to determine the angle
and throttle of a vehicle. Pilots can include one or more 
models to help direct the vehicles motion. 

'''




import os
import numpy as np
import keras
from ... import utils


import donkeycar as dk
from donkeycar import utils

class KerasPilot():
 
    def load(self, model_path):
        self.model = keras.models.load_model(model_path)
    
    
    def train(self, train_gen, val_gen, 
              saved_model_path, epochs=100, steps=10, ):
        
        """
        train_gen: generator that yields an array of images an array of 
        
        """

        #checkpoint to save model after each epoch
        save_best = keras.callbacks.ModelCheckpoint(saved_model_path, 
                                                    monitor='val_loss', 
                                                    verbose=0, 
                                                    save_best_only=True, 
                                                    mode='min')
        
        #stop training if the validation error stops improving.
        early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', 
                                                   min_delta=.0005, 
                                                   patience=4, 
                                                   verbose=1, 
                                                   mode='auto')
        
        #callbacks_list = [save_best, early_stop]
        callbacks_list = [save_best]
        
        hist = self.model.fit_generator(
                        train_gen, 
                        steps_per_epoch=steps, 
                        epochs=epochs, 
                        verbose=1, 
                        validation_data=val_gen,
                        callbacks=callbacks_list, 
                        validation_steps=steps*.2)
        return hist


class KerasCategorical(KerasPilot):
    def __init__(self, model=None, *args, **kwargs):
        super(KerasCategorical, self).__init__(*args, **kwargs)
        if model:
            self.model = model
        else:
            self.model = default_categorical()
        
    def run(self, img_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        angle_binned, throttle = self.model.predict(img_arr)
        #angle_certainty = max(angle_binned[0])
        angle_unbinned = utils.linear_unbin(angle_binned)
        return angle_unbinned, throttle[0][0]
    
    
    
class KerasLinear(KerasPilot):
    def __init__(self, *args, **kwargs):
        super(KerasLinear, self).__init__(*args, **kwargs)
        
    def run(self, img_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        angle, throttle = self.model.predict(img_arr)
        #angle_certainty = max(angle_binned[0])
        return angle[0][0], throttle[0][0]





def default_categorical():
    from keras.layers import Input, Dense, merge
    from keras.models import Model
    from keras.layers import Convolution2D, MaxPooling2D, Reshape, BatchNormalization
    from keras.layers import Activation, Dropout, Flatten, Dense
    
    img_in = Input(shape=(120, 160,3), name='img_in')
    x = img_in
    x = Convolution2D(24, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(32, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (3,3), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (3,3), strides=(1,1), activation='relu')(x)
    
    x = Flatten(name='flattened')(x)
    x = Dense(100, activation='relu')(x)
    x = Dropout(.1)(x)
    x = Dense(50, activation='relu')(x)
    x = Dropout(.1)(x)
    #categorical output of the angle
    angle_out = Dense(15, activation='softmax', name='angle_out')(x)
    
    #continous output of throttle
    throttle_out = Dense(1, activation='relu', name='throttle_out')(x)
    
    model = Model(inputs=[img_in], outputs=[angle_out, throttle_out])
    
    
    model.compile(optimizer='rmsprop',
                  loss={'angle_out': 'categorical_crossentropy', 
                        'throttle_out': 'mean_absolute_error'},
                  loss_weights={'angle_out': 0.9, 'throttle_out': .1})

    return model



def default_linear():
    from keras.layers import Input, Dense, merge
    from keras.models import Model
    from keras.layers import Convolution2D, MaxPooling2D, Reshape, BatchNormalization
    from keras.layers import Activation, Dropout, Flatten, Dense
    
    img_in = Input(shape=(120,160,3), name='img_in')
    x = img_in
    x = Convolution2D(24, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(32, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (3,3), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (3,3), strides=(1,1), activation='relu')(x)
    
    x = Flatten(name='flattened')(x)
    x = Dense(100, activation='linear')(x)
    x = Dropout(.1)(x)
    x = Dense(50, activation='linear')(x)
    x = Dropout(.1)(x)
    #categorical output of the angle
    angle_out = Dense(1, activation='linear', name='angle_out')(x)
    
    #continous output of throttle
    throttle_out = Dense(1, activation='linear', name='throttle_out')(x)
    
    model = Model(inputs=[img_in], outputs=[angle_out, throttle_out])
    
    
    model.compile(optimizer='rmsprop',
                  loss={'angle_out': 'mean_squared_error', 
                        'throttle_out': 'mean_squared_error'},
                  loss_weights={'angle_out': 0.9, 'throttle_out': .1})

    return model



def default_relu():
    from keras.layers import Input, Dense, merge
    from keras.models import Model
    from keras.layers import Convolution2D, MaxPooling2D, Reshape, BatchNormalization
    from keras.layers import Activation, Dropout, Flatten, Dense
    
    img_in = Input(shape=(120,160,3), name='img_in')
    x = img_in
    x = Convolution2D(24, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(32, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (5,5), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (3,3), strides=(2,2), activation='relu')(x)
    x = Convolution2D(64, (3,3), strides=(1,1), activation='relu')(x)
    
    x = Flatten(name='flattened')(x)
    x = Dense(100, activation='relu')(x)
    x = Dropout(.1)(x)
    x = Dense(50, activation='relu')(x)
    x = Dropout(.1)(x)
    #categorical output of the angle
    angle_out = Dense(1, activation='relu', name='angle_out')(x)
    
    #continous output of throttle
    throttle_out = Dense(1, activation='relu', name='throttle_out')(x)
    
    model = Model(inputs=[img_in], outputs=[angle_out, throttle_out])
    
    
    model.compile(optimizer='rmsprop',
                  loss={'angle_out': 'mean_squared_error', 
                        'throttle_out': 'mean_squared_error'},
                  loss_weights={'angle_out': 0.9, 'throttle_out': .1})

    return model

