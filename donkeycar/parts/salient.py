#from https://github.com/ermolenkodev/keras-salient-object-visualisation
import os
from keras import backend as K
import tensorflow as tf
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
from keras.layers import Input, Dense, merge
from keras.models import Model
from keras.layers import Convolution2D, MaxPooling2D, Reshape, BatchNormalization
from keras.layers import Activation, Dropout, Flatten, Dense
import cv2
import numpy as np

class SalientVis():
    '''
    Note, this part is quite tuned ust for the image dimensions and layers
    in our standard models. It will not reflect cropping or additional layers
    that might be in your model.
    '''

    def __init__(self, kerasPart):
        self.model = kerasPart.model
        self.init_salient(self.model)

    def run(self, image):
        if image is None:
            return
        image = self.draw_salient(image)
        image = image * 255
        image = image.astype('uint8')
        return image

    def init_salient(self, model):
        img_in = Input(shape=(120, 160, 3), name='img_in')
        x = img_in
        x = Convolution2D(24, (5,5), strides=(2,2), activation='relu', name='conv1')(x)
        x = Convolution2D(32, (5,5), strides=(2,2), activation='relu', name='conv2')(x)
        x = Convolution2D(64, (5,5), strides=(2,2), activation='relu', name='conv3')(x)
        x = Convolution2D(64, (3,3), strides=(2,2), activation='relu', name='conv4')(x)
        conv_5 = Convolution2D(64, (3,3), strides=(1,1), activation='relu', name='conv5')(x)
        self.convolution_part = Model(inputs=[img_in], outputs=[conv_5])

        for layer_num in ('1', '2', '3', '4', '5'):
            self.convolution_part.get_layer('conv' + layer_num).set_weights(model.get_layer('conv2d_' + layer_num).get_weights())
        
        self.inp = self.convolution_part.input                                           # input placeholder
        self.outputs = [layer.output for layer in self.convolution_part.layers[1:]]          # all layer outputs
        self.functor = K.function([self.inp], self.outputs)

        kernel_3x3 = tf.constant(np.array([
        [[[1]], [[1]], [[1]]], 
        [[[1]], [[1]], [[1]]], 
        [[[1]], [[1]], [[1]]]
        ]), tf.float32)

        kernel_5x5 = tf.constant(np.array([
                [[[1]], [[1]], [[1]], [[1]], [[1]]], 
                [[[1]], [[1]], [[1]], [[1]], [[1]]], 
                [[[1]], [[1]], [[1]], [[1]], [[1]]],
                [[[1]], [[1]], [[1]], [[1]], [[1]]],
                [[[1]], [[1]], [[1]], [[1]], [[1]]]
        ]), tf.float32)

        self.layers_kernels = {5: kernel_3x3, 4: kernel_3x3, 3: kernel_5x5, 2: kernel_5x5, 1: kernel_5x5}

        self.layers_strides = {5: [1, 1, 1, 1], 4: [1, 2, 2, 1], 3: [1, 2, 2, 1], 2: [1, 2, 2, 1], 1: [1, 2, 2, 1]}

        
    def compute_visualisation_mask(self, img):
        #from https://github.com/ermolenkodev/keras-salient-object-visualisation
        
        activations = self.functor([np.array([img])])
        activations = [np.reshape(img, (1, img.shape[0], img.shape[1], img.shape[2]))] + activations
        upscaled_activation = np.ones((3, 6))
        for layer in [5, 4, 3, 2, 1]:
            averaged_activation = np.mean(activations[layer], axis=3).squeeze(axis=0) * upscaled_activation
            output_shape = (activations[layer - 1].shape[1], activations[layer - 1].shape[2])
            x = tf.constant(
                np.reshape(averaged_activation, (1,averaged_activation.shape[0],averaged_activation.shape[1],1)),
                tf.float32
            )
            conv = tf.nn.conv2d_transpose(
                x, self.layers_kernels[layer],
                output_shape=(1,output_shape[0],output_shape[1], 1), 
                strides=self.layers_strides[layer], 
                padding='VALID'
            )
            with tf.Session() as session:
                result = session.run(conv)
            upscaled_activation = np.reshape(result, output_shape)
        final_visualisation_mask = upscaled_activation
        return (final_visualisation_mask - np.min(final_visualisation_mask))/(np.max(final_visualisation_mask) - np.min(final_visualisation_mask))

    def draw_salient(self, img):
        #from https://github.com/ermolenkodev/keras-salient-object-visualisation
        alpha = 0.004
        beta = 1.0 - alpha

        salient_mask = self.compute_visualisation_mask(img)
        salient_mask_stacked = np.dstack((salient_mask,salient_mask))
        salient_mask_stacked = np.dstack((salient_mask_stacked,salient_mask))
        blend = cv2.addWeighted(img.astype('float32'), alpha, salient_mask_stacked, beta, 0.0)
        return blend

    def shutdown(self):
        pass
        
