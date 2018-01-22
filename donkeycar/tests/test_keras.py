# -*- coding: utf-8 -*-
import pytest
from donkeycar.parts.keras import *
from donkeycar.utils import *
import numpy as np

@pytest.fixture
def pilot():
    kp = KerasPilot()
    return kp

def test_pilot_types(pilot):
    assert 1 == 1

def test_categorical():
    km = KerasCategorical()
    assert km.model is not None
    img = get_test_img(km.model)
    km.run(img)

def test_categorical_med():
    input_shape=(64, 64, 1)
    km = KerasCategorical(input_shape=input_shape)
    assert km.model is not None
    img = get_test_img(km.model)
    km.run(img)

def test_categorical_tiny():
    input_shape=(32, 32, 1)
    km = KerasCategorical(input_shape=input_shape)
    assert km.model is not None
    img = get_test_img(km.model)
    km.run(img)
    
def test_linear():
    km = KerasLinear()
    assert km.model is not None   
    img = get_test_img(km.model)
    km.run(img)

def test_imu():
    km = KerasIMU()
    assert km.model is not None
    img = get_test_img(km.model)
    imu = np.random.rand(6).tolist()
    km.run(img, *imu)

def test_rnn():
    km = KerasRNN_LSTM()
    assert km.model is not None
    img = get_test_img(km.model)
    km.run(img)
    
def test_3dconv():
    km = Keras3D_CNN()
    assert km.model is not None
    img = get_test_img(km.model)
    km.run(img)
