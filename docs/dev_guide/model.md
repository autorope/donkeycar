# How to build your own model

* [Overview](model.md#overview)
* [Constructor](model.md#constructor)
* [Training Interface](model.md#training interface)
* [Parts Interface](model.md#parts interface)
* [Example](model.md#example)

## Overview

You might want to write your own model:

* If you find the models that ship with donkey not sufficient, and you want to
  experiment with your own model infrastructure
* If you want to add more input data to the model because your car has more
  sensors

## Constructor

Models are located in `donkeycar/parts/keras.py`. Your own model needs to
inherit from `KerasPilot` and initialize your model:

```python
class KerasSensors(KerasPilot):
    def __init__(self, input_shape=(120, 160, 3), num_sensors=2):
        super().__init__()
        self.num_sensors = num_sensors
        self.model = self.create_model(input_shape)
```
Here, you implement the [keras model](https://www.tensorflow.org/guide/keras/sequential_model)
in the member function `create_model()`. The model needs to have labelled input
and output tensors. These are required for the training to work.


## Training interface

What is required for your model to work, are the following functions:

```python
def compile(self):
    self.model.compile(optimizer=self.optimizer, metrics=['accuracy'],
                       loss={'angle_out': 'categorical_crossentropy',
                             'throttle_out': 'categorical_crossentropy'},
                       loss_weights={'angle_out': 0.5, 'throttle_out': 0.5})
```

The `compile` function tells keras how to define the loss function for training.
We are using the `KerasCategorical` model as an example. The loss function here
makes explicit usage of the output tensors of the
model (`angle_out, throttle_out`).

```python
def x_transform(self, record: TubRecord):
    img_arr = record.image(cached=True)
    return img_arr
```

In this function you define how to extract the input data from your
recorded data. This data is usually called `X` in the ML frame work . We have
shown the implementation in the base class which works for all models that have
only the image as input. 

The function returns a single data item if the model has only one input. You 
need to return a tuple if your model uses more input data.
**Note:** _If your model has more inputs, the tuple needs to have the image in 
the first place._ 

```python
def y_transform(self, record: TubRecord):
    angle: float = record.underlying['user/angle']
    throttle: float = record.underlying['user/throttle']
    return angle, throttle
```
In this function you specify how to extract the `y` values (i.e. target
values) from your recorded data.


```python
def x_translate(self, x: XY) -> Dict[str, Union[float, np.ndarray]]:
    return {'img_in': x}
```
Here we require a translation of how the `X` value that you extracted above will
be fed into `tf.data`. Note, `tf.data` expects a dictionary if the model has
more than one input variable, so we have chosen to use dictionaries also in the
one-argument case for consistency. Above we have shown the implementation in the
base class which works for all models that have only the image as input. You
don't have to overwrite neither `x_transform` nor
`x_translate` if your model only uses the image as input data.
**Note:** _the keys of the dictionary must match the name of the **input**  
layers in the model._

```python
def y_translate(self, y: XY) -> Dict[str, Union[float, np.ndarray]]:
    if isinstance(y, tuple):
        angle, throttle = y
        return {'angle_out': angle, 'throttle_out': throttle}
    else:
        raise TypeError('Expected tuple')
```
Similar to the above, this provides the translation of the `y` data into the
dictionary required for `tf.data`. This example shows the implementation of
`KerasLinear`.
**Note:** _the keys of the dictionary must match the name of the **output**
layers in the model._

```python
def output_shapes(self):
    # need to cut off None from [None, 120, 160, 3] tensor shape
    img_shape = self.get_input_shape()[1:]
    shapes = ({'img_in': tf.TensorShape(img_shape)},
              {'angle_out': tf.TensorShape([15]),
               'throttle_out': tf.TensorShape([20])})
    return shapes
```
This function returns a tuple of _two_ dictionaries that tells tensorflow which
shapes are used in the model. We have shown the example of the 
`KerasCategorical` model here.
**Note 1:** _The keys of the two dictionaries must match the name of the
**input** and **output** layers in the model._
**Note 2:** _Where the model returns scalar numbers, the corresponding 
type has to be `tf.TensorShape([])`._


## Parts interface

In the car application the model is called through the `run()` function. That
function is already provided in the base class where the normalisation of the
input image is happening centrally. Instead, the derived classes have to
implement
`inference()` which works on the normalised data. If you have additional data
that needs to be normalised, too, you might want to override `run()` as well.
```python
def inference(self, img_arr, other_arr):
    img_arr = img_arr.reshape((1,) + img_arr.shape)
    outputs = self.model.predict(img_arr)
    steering = outputs[0]
    throttle = outputs[1]
    return steering[0][0], throttle[0][0]
```
Here we are showing the implementation of the linear model. Please note that 
the input tensor shape always contains the batch dimension in the first 
place, hence the shape of the input image is adjusted from 
`(120, 160, 3) -> (1, 120, 160, 3)`.
**Note:** _If you are passing another array in the`other_arr` variable, you will
have to do a similar re-shaping.


## Example
Let's build a new donkey model which is based on the standard linear model 
but has following changes w.r.t. input data and network design:

1. The model takes an additional vector of input data that represents a set 
   of values from distance sensors which are attached to the front of the car.
   
2. The model adds a couple of more feed-forward layers to combine the CNN 
   layers of the vision system with the distance sensor data.

### Building the model using keras   
So here is the example model:
```python
class KerasSensors(KerasPilot):
    def __init__(self, input_shape=(120, 160, 3), num_sensors=2):
        super().__init__()
        self.num_sensors = num_sensors
        self.model = self.create_model(input_shape)

    def create_model(self, input_shape):
        drop = 0.2
        img_in = Input(shape=input_shape, name='img_in')
        x = core_cnn_layers(img_in, drop)
        x = Dense(100, activation='relu', name='dense_1')(x)
        x = Dropout(drop)(x)
        x = Dense(50, activation='relu', name='dense_2')(x)
        x = Dropout(drop)(x)
        # up to here, this is the standard linear model, now we add the
        # sensor data to it
        sensor_in = Input(shape=(self.num_sensors, ), name='sensor_in')
        y = sensor_in
        z = concatenate([x, y])
        # here we add two more dens layers
        z = Dense(50, activation='relu', name='dense_3')(z)
        z = Dropout(drop)(z)
        z = Dense(50, activation='relu', name='dense_4')(z)
        z = Dropout(drop)(z)
        # two outputs for angle and throttle
        outputs = [
            Dense(1, activation='linear', name='n_outputs' + str(i))(z)
            for i in range(2)]

        # the model needs to specify the additional input here
        model = Model(inputs=[img_in, sensor_in], outputs=outputs)
        return model

    def compile(self):
        self.model.compile(optimizer=self.optimizer, loss='mse')

    def inference(self, img_arr, other_arr):
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        sens_arr = other_arr.reshape((1,) + other_arr.shape)
        outputs = self.model.predict([img_arr, sens_arr])
        steering = outputs[0]
        throttle = outputs[1]
        return steering[0][0], throttle[0][0]

    def x_transform(self, record: TubRecord) -> XY:
        img_arr = super().x_transform(record)
        # for simplicity we assume the sensor data here is normalised
        sensor_arr = np.array(record.underlying['sensor'])
        # we need to return the image data first
        return img_arr, sensor_arr

    def x_translate(self, x: XY) -> Dict[str, Union[float, np.ndarray]]:
        assert isinstance(x, tuple), 'Requires tuple as input'
        # the keys are the names of the input layers of the model
        return {'img_in': x[0], 'sensor_in': x[1]}

    def y_transform(self, record: TubRecord):
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        return angle, throttle

    def y_translate(self, y: XY) -> Dict[str, Union[float, np.ndarray]]:
        if isinstance(y, tuple):
            angle, throttle = y
            # the keys are the names of the output layers of the model
            return {'n_outputs0': angle, 'n_outputs1': throttle}
        else:
            raise TypeError('Expected tuple')

    def output_shapes(self):
        # need to cut off None from [None, 120, 160, 3] tensor shape
        img_shape = self.get_input_shape()[1:]
        # the keys need to match the models input/output layers
        shapes = ({'img_in': tf.TensorShape(img_shape),
                   'sensor_in': tf.TensorShape([self.num_sensors])},
                  {'n_outputs0': tf.TensorShape([]),
                   'n_outputs1': tf.TensorShape([])})
        return shapes
```
We could have inherited from `KerasLinear` which would provide the 
implementation of `y_transform(), y_translate(), compile()`. The model 
requires the sensor data to be an array in the TubRecord with key `"sensor"`.

### Creating a tub

Because we don't have a tub with sensor data, let's create one with fake 
sensor entries:
```python
import os
import tarfile
import numpy as np
from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.types import TubRecord
from donkeycar.config import load_config


if __name__ == '__main__':
    # put your path to your car app
    my_car = os.path.expanduser('~/mycar')
    cfg = load_config(os.path.join(my_car, 'config.py'))
    # put your path to donkey project
    tar = tarfile.open(os.path.expanduser(
        '~/Python/donkeycar/donkeycar/tests/tub/tub.tar.gz'))
    tub_parent = os.path.join(my_car, 'data2/')
    tar.extractall(tub_parent)
    tub_path = os.path.join(tub_parent, 'tub')
    tub1 = Tub(tub_path)
    tub2 = Tub(os.path.join(my_car, 'data2/tub_sensor'),
               inputs=['cam/image_array', 'user/angle', 'user/throttle',
                       'sensor'],
               types=['image_array', 'float', 'float', 'list'])

    for record in tub1:
        t_record = TubRecord(config=cfg,
                             base_path=tub1.base_path,
                             underlying=record)
        img_arr = t_record.image(cached=False)
        record['sensor'] = list(np.random.uniform(size=2))
        record['cam/image_array'] = img_arr
        tub2.write_record(record)
```

### Making the model available
We don't have a dynamic factory yet, so we need to add the new model into the 
function `get_model_by_type()` in the module `donkeycar/utils.py`:
```python
...
elif model_type == 'sensor':
    kl = KerasSensors(input_shape=input_shape)
...
```

### Go train
In your car app folder now the following should work:
`donkey train --tub data2/tub_sensor --model models/pilot.h5 --type sensor`
Because of the random values in the data the model will not converge quickly,
the goal here is to get it working in the frame work.


## Support and discussions
Please join the [Discord](https://discord.gg/dpvYHhpV2w) Donkey Car group for 
support and discussions.



