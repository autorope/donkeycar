# Keras Parts

These parts encapsulate models defined using the [Keras](https://keras.io/) high level api. They are intended to be used with the Tensorflow backend. The parts are designed to use the trained artificial neural network to reproduce the steering and throttle given the image the camera sees. They are created by using the [train command](/guide/train_autopilot/).

## Keras Categorical

This model type is created with the --type=catagorical. 

The KerasCategorical pilot breaks the steering and throttle decisions into discreet
    angles and then uses categorical cross entropy to train the network to activate a single
    neuron for each steering and throttle choice. This can be interesting because we
    get the confidence value as a distribution over all choices.
    This uses the dk.utils.linear_bin and dk.utils.linear_unbin to transform continuous
    real numbers into a range of discreet values for training and runtime.
    The input and output are therefore bounded and must be chosen wisely to match the data.
    The default ranges work for the default setup. But cars which go faster may want to
    enable a higher throttle range. And cars with larger steering throw may want more bins.
    
This model was the original model, with some modifications, when Donkey was first created. 

#### Pros: 

* It has some benefits of showing the confidense as a distribution via the makemovie command. 
* It has been very robust.
* In some cases this model has learned thottle control better than other models.
* Performs well in a limited compute environment like the Pi3.


#### Cons: 

* Suffers from some arbitrary limitations of the chosen limits for number of categories, and thottle upper limit. 

#### Model Summary:

Input: Image

Network: 5 Convolution layers followed by two dense layers before output

Output: Two dense layers, 16, and 20 w categorical output

## Keras Linear

This model type is created with the --type=linear. 

The KerasLinear pilot uses one neuron to output a continous value via the 
Keras Dense layer with linear activation. One each for steering and throttle.
The output is not bounded.

#### Pros: 

* Steers smoothly. 
* It has been very robust.
* Performs well in a limited compute environment like the Pi3.
* No arbitrary limits to steering or throttle.

#### Cons: 

* May sometimes fail to learn throttle well.

#### Model Summary:

Input: Image

Network: 5 Convolution layers followed by two dense layers before output

Output: Two dense layers with one scalar output each with linear activation for steering and throttle.


## Keras IMU

This model type is created with the --type=imu. 

The KerasIMU pilot is very similar to the KerasLinear model, except that it takes intertial measurment data in addition to images when learning to drive.
This gives our stateless model some additional information about the motion of the vehicle.

This can be a good starting point example of ingesting more data into your models.

#### Pros: 

* Steers very smoothly. 
* Performs well in a limited compute environment like the Pi3.
* No arbitrary limits to steering or throttle.
* Gives additional state to the model, which might help it come to a stop at a stop sign.

#### Cons: 

* Driving quality will suffer if noisy imu is used.

#### Model Summary:

Input: Image, vector of linear and angular acceleration

Network: 5 Convolution layers followed by two dense layers before output, Vector data is followed by 3 dense layers then concatenating before 2 dense control layers and after conv2d layers.

Output: Two dense layers with one scalar output each with linear activation for steering and throttle.


## Keras Latent

This model type is created with the --type=latent. 

The KerasLatent pilot tries to force the model to learn a latent vector in addition to driving. This latent vector is a bottleneck in a CNN that then tries to reproduce the given input image and produce driving commands. These dual tasks could produce a model that learns to distill the driving scene and perhaps better abstract to a new track.

#### Pros: 

* Steers smoothly. 
* Performs well in a limited compute environment like the Pi3.
* No arbitrary limits to steering or throttle.
* Image output a measure of what the model has deemed important in the scene.

#### Cons: 

* Needs more testing to prove theory.

#### Model Summary:

Input: Image

Network: 5 Convolution layers bottleneck to a 10x1x1 vector, followed by 6Conv2dTranspose layers before outputing to a image and 3 dense layers and driving controls.

Output: Two dense layers with one scalar output each with linear activation for steering and throttle. Outputs an image.


## Keras RNN

This model type is created with the --type=rnn. 

The KerasRNN pilot uses a sequence of images to control driving rather than just a single frame. The number of images used is controlled by the SEQUENCE_LENGTH value in myconfig.py.

#### Pros: 

* Steers very smoothly. 
* Can train to a lower loss

#### Cons: 

* Performs worse in a limited compute environment like the Pi3.
* Takes longer to train.

#### Model Summary:

Input: Image

Network: 4 time distributed Convolution layers, followed by 2 LSTM layers, 3 dense layers, and driving controls.

Output: One dense layer with two scalar outputs for steering and throttle.


## Keras 3D

This model type is created with the --type=3d. 

The Keras3D_CNN pilot uses a sequence of images to control driving rather than just a single frame. The number of images used is controlled by the SEQUENCE_LENGTH value in myconfig.py. Instead of 2d convolutions like most other models, this uses a 3D convolution across layers.

#### Pros: 

* Steers very smoothly.
* Can train to a lower loss.

#### Cons: 

* Performs worse in a limited compute environment like the Pi3.
* Takes longer to train.

#### Model Summary:

Input: Image

Network: 4 3D Convolution layers each followed by max pooling, followed by 2 dense layers, and driving controls.

Output: One dense layer with two scalar outputs for steering and throttle.


## Keras Behavior

This model type is created with the --type=behavior. 

The KerasBehavioral pilot takes an image and a vector as input. The vector is one hot activated vector of commands. This vector might be of length two and have two states, one for left lane driving and one for right lane driving. Then during training one element of the vector is activated while the desired behavior is demonstrated. This vector is defined in myconfig.py BEHAVIOR_LIST. BEHAVIOR_LED_COLORS must match the same length and can be useful when showing the current state. TRAIN_BEHAVIORS must be set to True.

#### Pros: 

* Can create a model which can perform multiple tasks 

#### Cons: 

* Takes more effort to train.

#### Model Summary:

Input: Image, Behavior vector

Network: 5 Convolution layers, followed by 2 dense layers, and driving controls.

Output: Categorical steering, throttle output similar to Categorical keras model.


## Keras Localizer

This model type is not created without some code modification. 

The KerasLocalizer pilot is very similar to the Keras Linear model, except that it learns to output it's location as a category.
This category is arbitrary, but has only been tested as a 0-9 range segment of the track. This requires that the driving data is marked up with a category label for location. This could supply some higher level logic with track location, for driving stategy, lap counting, or other.

#### Pros: 

* Steers smoothly.
* Performs well in a limited compute environment like the Pi3.
* No arbitrary limits to steering or throttle.
* Location to supply some higher level logic.

#### Cons: 

* May sometimes fail to learn throttle well.

#### Model Summary:

Input: Image

Network: 5 Convolution layers followed by two dense layers before output

Output: Two dense layers with one scalar output each with linear activation for steering and throttle. One categorical output for location.

