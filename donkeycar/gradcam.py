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
            if (i % 100 == 0): print('Processing %.2f% ...'.format(i*100./len(idx)))
            img = mix_heatmap(img_in, heatmap)
            img = cv2.resize(img, (0, 0), fx = 4, fy = 4, interpolation = cv2.INTER_LINEAR)
            cv2.imwrite(os.path.join(temp_dir, '{0:06d}.jpg'.format(i)), img)

        print("Generate Grad-CAM video {} ...".format(out))
        call("ffmpeg -i {}/%06d.jpg -vf fps=25 {}".format(temp_dir, out).split())

    finally:
        shutil.rmtree(temp_dir)

