# -*- coding: utf-8 -*-

from donkeycar.parts.keras import *
from donkeycar.utils import *
import numpy as np


def test_categorical():
    km = KerasCategorical()
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
    km.run(img, imu)


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


def test_localizer():
    km = KerasLocalizer()
    assert km.model is not None   
    img = get_test_img(km.model)
    km.run(img)




