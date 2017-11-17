import os
import numpy as np
import keras
import donkeycar as dk
from donkeycar.parts.keras import KerasPilot

class KerasRNN_LSTM(KerasPilot):
    def __init__(self, seq_length=3, num_outputs=2, *args, **kwargs):
        super(KerasRNN_LSTM, self).__init__(*args, **kwargs)
        self.model = rnn_lstm(seq_length=seq_length, num_outputs=num_outputs)
        self.seq_length = seq_length
        self.img_seq = []

    def run(self, img_arr):
        while len(self.img_seq) < self.seq_length:
            self.img_seq.append(img_arr)

        self.img_seq = self.img_seq[1:]
        self.img_seq.append(img_arr)
        
        img_arr = np.array(self.img_seq).reshape(1, self.seq_length, 120, 160, 3 )
        outputs = self.model.predict([img_arr])
        steering = outputs[0][0]
        throttle = outputs[0][1]
        #print(steering, throttle)
        return steering, throttle
  
def rnn_lstm_one(seq_length=3, num_outputs=2, image_shape=(120,160,3)):

    from numpy.random import seed
    seed(1)
    from tensorflow import set_random_seed
    set_random_seed(2)

    from keras.layers import Input, Dense
    from keras.models import Sequential
    from keras.layers import Convolution2D, MaxPooling2D, Reshape, BatchNormalization, Merge
    from keras.layers import Activation, Dropout, Flatten, Cropping2D, Lambda
    from keras.layers.merge import concatenate
    from keras.layers import LSTM
    from keras.layers.wrappers import TimeDistributed as TD

    img_seq_shape = (seq_length,) + image_shape   
    img_in = Input(batch_shape = img_seq_shape, name='img_in')
    
    x = Sequential()
    x.add(TD(Cropping2D(cropping=((60,0), (0,0))), input_shape=img_seq_shape )) #trim 60 pixels off top
    x.add(TD(Convolution2D(24, (5,5), strides=(2,2), activation='relu')))
    x.add(TD(Convolution2D(32, (5,5), strides=(2,2), activation='relu')))
    x.add(TD(Convolution2D(32, (3,3), strides=(2,2), activation='relu')))
    x.add(TD(Convolution2D(32, (3,3), strides=(1,1), activation='relu')))
    x.add(TD(MaxPooling2D(pool_size=(2, 2))))
    x.add(TD(Flatten(name='flattened')))
    x.add(TD(Dense(100, activation='relu')))
    x.add(TD(Dropout(.1)))
      
    x.add(LSTM(128, return_sequences=True, name="LSTM_seq"))
    x.add(Dropout(.1))
    x.add(LSTM(128, return_sequences=False, name="LSTM_out"))
    x.add(Dropout(.1))
    x.add(Dense(50, activation='relu'))
    x.add(Dropout(.1))
    x.add(Dense(num_outputs, activation='linear', name='model_outputs'))
    
    x.compile(optimizer='adam', loss='mse')
    
    print(x.summary())

    return x

def rnn_lstm(seq_length=3, num_outputs=2, image_shape=(120,160,3)):

    from keras.layers import Input, Dense
    from keras.models import Sequential
    from keras.layers import Convolution2D, MaxPooling2D, Reshape, BatchNormalization, Merge
    from keras.layers import Activation, Dropout, Flatten, Cropping2D, Lambda
    from keras.layers.merge import concatenate
    from keras.layers import LSTM
    from keras.layers.wrappers import TimeDistributed as TD

    img_seq_shape = (seq_length,) + image_shape   
    img_in = Input(batch_shape = img_seq_shape, name='img_in')
    
    x = Sequential()
    x.add(TD(Cropping2D(cropping=((60,0), (0,0))), input_shape=img_seq_shape )) #trim 60 pixels off top
    x.add(TD(Convolution2D(24, (5,5), strides=(2,2), activation='relu')))
    x.add(TD(Convolution2D(32, (5,5), strides=(2,2), activation='relu')))
    x.add(TD(Convolution2D(32, (3,3), strides=(2,2), activation='relu')))
    x.add(TD(Convolution2D(32, (3,3), strides=(1,1), activation='relu')))
    #x.add(TD(Convolution2D(32, (3,3), strides=(1,1), activation='relu')))
    x.add(TD(MaxPooling2D(pool_size=(2, 2))))
    x.add(TD(Flatten(name='flattened')))
    x.add(TD(Dense(100, activation='relu')))
    x.add(TD(Dropout(.1)))
      
    x.add(LSTM(128, return_sequences=True, name="LSTM_seq"))
    x.add(Dropout(.1))
    x.add(LSTM(128, return_sequences=False, name="LSTM_out"))
    x.add(Dropout(.1))
    x.add(Dense(128, activation='relu'))
    x.add(Dropout(.1))
    x.add(Dense(64, activation='relu'))
    x.add(Dense(10, activation='relu'))
    x.add(Dense(num_outputs, activation='linear', name='model_outputs'))
    
    x.compile(optimizer='rmsprop', loss='mse')
    
    print(x.summary())

    return x

