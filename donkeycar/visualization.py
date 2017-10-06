from keras.preprocessing import image
from keras.models import load_model
from tensorflow.python.framework import ops
import keras.backend as K
import datetime
import tensorflow as tf
import numpy as np
import keras
import sys
import cv2
import os
import tempfile
import shutil
from subprocess import call

import donkeycar as dk

#Grad-CAM visualization https://github.com/jacobgil/keras-grad-cam

def target_category_loss(x, category_index, nb_classes):
    return tf.multiply(x, K.one_hot([category_index], nb_classes))

def target_category_loss_output_shape(input_shape):
    return input_shape

def normalize(x):
    # utility function to normalize a tensor by its L2 norm
    return x / (K.sqrt(K.mean(K.square(x))) + 1e-5)

def load_image(img_path):
    img = image.load_img(img_path, target_size=(120, 160))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    return x

def register_gradient():
    if "GuidedBackProp" not in ops._gradient_registry._registry:
        @ops.RegisterGradient("GuidedBackProp")
        def _GuidedBackProp(op, grad):
            dtype = op.inputs[0].dtype
            return grad * tf.cast(grad > 0., dtype) * \
                tf.cast(op.inputs[0] > 0., dtype)

def compile_saliency_function(model, activation_layer='conv2d_5'):
    input_img = model.input
    layer_dict = dict([(layer.name, layer) for layer in model.layers[1:]])
    layer_output = layer_dict[activation_layer].output
    max_output = K.max(layer_output, axis=3)
    saliency = K.gradients(K.sum(max_output), input_img)[0]
    return K.function([input_img, K.learning_phase()], [saliency])

def modify_backprop(model, name):
    g = tf.get_default_graph()
    with g.gradient_override_map({'Relu': name}):

        # get layers that have an activation
        layer_dict = [layer for layer in model.layers[1:]
                      if hasattr(layer, 'activation')]

        # replace relu activation
        for layer in layer_dict:
            if layer.activation == keras.activations.relu:
                layer.activation = tf.nn.relu

        # re-instanciate a new model
        new_model = load_model(modelpath)
    return new_model

functions = {}

def grad_cam(input_model, image, category_index, layer_name):
    model = input_model
    nb_classes = 15
    f = None

    if category_index in functions:
        f = functions[category_index]
    else:
        loss = model.output[0][:, category_index]
        conv_output = model.get_layer(layer_name).output
        grads = normalize(K.gradients(loss, conv_output)[0])
        f = K.function([model.input, K.learning_phase()], [conv_output, grads])
        functions[category_index] = f

    output, grads_val = f([image, 1])
    output, grads_val = output[0, :], grads_val[0, :, :, :]

    weights = np.mean(grads_val, axis = (0, 1))
    cam = np.ones(output.shape[0 : 2], dtype = np.float32)

    for i, w in enumerate(weights):
        cam += w * output[:, :, i]

    cam = cv2.resize(cam, (160, 120))
    cam = np.maximum(cam, 1)
    heatmap = cam / np.max(cam)

    #Return to BGR [0..255] from the preprocessed image
    image = image[0, :]
    #image += 0.5
    #image *= 255
    #image -= np.min(image)
    #image = np.minimum(image, 255)

    cam = mix_heatmap(image, heatmap)
    return cam, heatmap


def mix_heatmap(img, heatmap):
    if len(img.shape) > 3:
        img = img[0]
    cam = cv2.applyColorMap(np.uint8(255*heatmap), cv2.COLORMAP_JET)
    cam = np.float32(cam) + np.float32(img)
    cam = 255 * cam / np.max(cam)
    cam = np.uint8(cam)
    return cam

def gradcam_video(cfg, tub_path, model_path, out):
    temp_dir = tempfile.mkdtemp()
    if shutil.which('ffmpeg') is None:
        print("ffmpge is not found. Please make sure it is installed and in PATH")
        sys.exit(-1)

    try:
        model = load_model(model_path)
        tub = dk.parts.Tub(os.path.join(cfg.DATA_PATH, tub_path))
    
        idx = tub.get_index(shuffled=False)
        for i in range(len(idx)):
            rec = tub.get_record(idx[i])
            img_in = rec['cam/image_array']
            img_in = img_in.reshape((1,) + img_in.shape)
            predicted_angle, _ = model.predict(img_in)
            predicted_class = np.argmax(predicted_angle[0])
            cam, heatmap = grad_cam(model, img_in, predicted_class, 'conv2d_5')
            if (i % 100 == 0): print('Processing {}% ...'.format(int(i*100./len(idx))))
            img = cv2.resize(cam, (0, 0), fx = 4, fy = 4, interpolation = cv2.INTER_LINEAR)
            cv2.imwrite(os.path.join(temp_dir, '{0:06d}.jpg'.format(i)), img)

        print("Generate Grad-CAM video {} ...".format(out))
        call("ffmpeg -i {}/%06d.jpg -vf fps=25 {}".format(temp_dir, out).split())

    finally:
        shutil.rmtree(temp_dir)


# Visual Back propagation https://github.com/alanswx/VisualBackPropKeras

from keras.models import *
from keras.callbacks import *
from keras.layers import Lambda, Convolution2D, Activation, Dropout, Flatten, Dense
from keras.layers import Dense, Lambda, ELU
from keras.layers import Dense, Activation, Reshape, Merge
from keras.layers.pooling import MaxPooling2D, AveragePooling1D
from keras.layers import Merge
import keras.backend as K
import cv2
import argparse
import pickle
from keras.models import load_model
from keras.layers import Convolution2D, MaxPooling2D, Activation, Lambda, Input, Deconvolution2D, Flatten, Dense, Reshape, ZeroPadding2D, Cropping2D
from keras.layers import Merge
from keras.models import Sequential
from keras import backend as K
from keras.layers import merge
import keras

from distutils.version import LooseVersion

import numpy as np
import matplotlib.pyplot as plt
import cv2  # only used for loading the image, you can use anything that returns the image as a np.ndarray
from PIL import Image, ImageEnhance, ImageOps

import matplotlib.cm as cm
from keras.models import Model


def almostEquals(a,b,thres=50):
    return all(abs(a[i]-b[i])<thres for i in range(len(a)))


#
#  Create the models
#

def activationModel(model):
  # grab the conv layers
  current_stack=[]
  act_stack=[]
  for layer in model.layers:
    if layer.name.startswith("conv"):
        current_stack.insert(0, layer)
        #print('*********8')
        #print(layer.outbound_nodes[0].outbound_layer.name)
        nextlayer=layer.outbound_nodes[0].outbound_layer;
        #print(nextlayer.name)
        if (nextlayer.name.startswith("elu")):
           act_stack.insert(0, nextlayer)
        elif (nextlayer.name.startswith("activ")):
           act_stack.insert(0, nextlayer)
        else:
           act_stack.insert(0, layer)

  print("current stack:")
  for layer in current_stack:
    print(layer.name)
    print(layer.outbound_nodes[0].outbound_layer.name)
  print("act stack:")
  for layer in act_stack:
    print(layer.name)
  print("---------")



  lastone=None
  #  hold onto last one..
  for i, layer in enumerate(current_stack):
    #print(layer.name,i)
    our_shape=(layer.output_shape[1],layer.output_shape[2],1)
    hidden_layer = act_stack[i]
    #print(hidden_layer.name)
    #print(layer.name)
    #print(our_shape)
    # average this layer
    name='lambda_new_'+str(i)
    c1=Lambda(lambda xin: K.mean(xin,axis=3),name=name)(hidden_layer.output)
    name='reshape_new_'+str(i)
    r1=Reshape(our_shape,name=name)(c1)
    #lastone=r1
    if (i!=0):
       # if we aren't the bottom, multiply by output of layer below
       print("multiply")
       name='multiply_'+str(i)
       r1 = merge([r1,lastone], mode='mul', name = name)
       lastone=r1


    if (i<len(current_stack)-1):
        print('do deconv')
        # deconv to the next bigger size
        bigger_shape=current_stack[i+1].output_shape
    else:
        bigger_shape=model.input_shape


    bigger_shape=(bigger_shape[0],bigger_shape[1],bigger_shape[2],1)

    if (LooseVersion(keras.__version__) > LooseVersion("2.0.0")):
      print ("Keras 2")
      subsample=current_stack[i].strides
      nb_row,nb_col=current_stack[i].kernel_size
    else:
      subsample=current_stack[i].subsample
      nb_row=current_stack[i].nb_row
      nb_col=current_stack[i].nb_col
    #print("deconv params:")
    #print("subsample:",subsample)
    #nb_row,nb_col=current_stack[i].kernel_size
    #print("nb_col,nb_row:",nb_col,nb_row)
    #print("bigger_shape:",bigger_shape)
    name='deconv_new_'+str(i)
    print(name)
    print('Deconvolution2D(1,',nb_row, nb_col,'output_shape=',bigger_shape,'subsample= ',subsample,'border_mode=valid','activation=relu','init=one','name=',name)
    d1 = Deconvolution2D(1, nb_row, nb_col,output_shape=bigger_shape,subsample= subsample,border_mode='valid',activation='relu',init='one',name=name)(r1)

    if (d1._keras_shape[1]!=bigger_shape[1] or d1._keras_shape[2]!=bigger_shape[2]):
       print("d1:",d1._keras_shape)
       pad=0
       if (d1._keras_shape[1]<bigger_shape[1]):
         if (d1._keras_shape[2]!=bigger_shape[2]):
            pad=1
         else:
            pad=0
         z1 = ZeroPadding2D(padding=(1, pad), data_format=None)(d1)
         c1 = Cropping2D(cropping=((1, 0), (pad, 0)) , data_format=None)(z1)
         print("z1:",z1._keras_shape)
       else:
         print("making smaller")
         padx=d1._keras_shape[1] - bigger_shape[1]
         pady=d1._keras_shape[2] - bigger_shape[2]
         print("padx,pady",padx,pady)
         c1 = Cropping2D(cropping=((padx, 0), (pady, 0)) , data_format=None)(d1)
       print("c1:",c1._keras_shape)
       lastone=c1
    else:
       lastone=d1

  model2 = Model(input=model.input,output=[lastone])
  model2.summary()

  return model2


def highlightBackProp(image,model2):

    #steering_angle = float(model.predict(image[None, :, :, :], batch_size=1))
    #   print(image.shape)
    #image = cv2.resize(image, (256, 256) )
    oldimage = image
    #image = cv2.resize(image, (200, 66) )

    # transpose if model is other way
    count, h, w, ch = model2.inputs[0].get_shape()
    ih, iw, ich = image.shape
    if h == ich and ch == ih:
       image= image.transpose()

    #print(image.shape)
    m1d = model2.predict(image[None, :, :, :], batch_size=1)
    #print(m1d.shape)
    m1d = np.squeeze(m1d, axis=0)
    m1d = np.squeeze(m1d, axis=2)
    #m1d = cv2.resize(image, (120, 160) )

    #m1d=np.resize(m1d,(120,160))
    #print(m1d.shape)

    #print(m1d)
    #plt.hist(m1d[::-1])
    #plt.show()
    #print(m1d.max())
    #print(m1d.min())
    o2=overlay = Image.fromarray(cm.Reds(m1d/m1d.max(), bytes=True))
    #o2= o2.convert("RGB")
    #return o2
    #plt.imshow(o2);
    #plt.show();

    pixeldata = list(overlay.getdata())

    for i,pixel in enumerate(pixeldata):
        if almostEquals(pixel[:3], (255,255,255)):
            pixeldata[i] = (255,255,255,0)
        else:
            pixeldata[i]= (pixel[0],pixel[1],pixel[2],128)

    overlay.putdata(pixeldata)
    #obig= cv2.resize(overlay, (320, 160) )

    carimg = Image.fromarray(np.uint8(image))
    #carimg = Image.fromarray(np.uint8(oldimage))
    carimg = carimg.convert("RGBA")
    new_img2=Image.alpha_composite(carimg, overlay)
    new_img2= new_img2.convert("RGB")
    o2= o2.convert("RGB")
    #plt.imshow(o2);
    #plt.show();
    return np.array(new_img2)

def backprop_video(cfg, tub_path, model_path, out):
    temp_dir = tempfile.mkdtemp()
    if shutil.which('ffmpeg') is None:
        print("ffmpge is not found. Please make sure it is installed and in PATH")
        sys.exit(-1)

    try:
        model = load_model(model_path)
        actModel = activationModel(model)
        tub = dk.parts.Tub(os.path.join(cfg.DATA_PATH, tub_path))
    
        idx = tub.get_index(shuffled=False)
        for i in range(len(idx)):
            rec = tub.get_record(idx[i])
            img_in = rec['cam/image_array']
            img = highlightBackProp(img_in, actModel)
            img = cv2.resize(img, (0, 0), fx = 4, fy = 4, interpolation = cv2.INTER_LINEAR)
            cv2.imwrite(os.path.join(temp_dir, '{0:06d}.jpg'.format(i)), img)
            if (i % 100 == 0): print('Processing {}% ...'.format(int(i*100./len(idx))))

        print("Generate visual back propgation video {} ...".format(out))
        call("ffmpeg -i {}/%06d.jpg -vf fps=25 {}".format(temp_dir, out).split())

    finally:
        shutil.rmtree(temp_dir)

def visualize(cfg, tub_path, model_path, out, gradcam):
    if gradcam:
        gradcam_video(cfg, tub_path, model_path, out)
    else:
        backprop_video(cfg, tub_path, model_path, out)

