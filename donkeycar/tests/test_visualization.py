#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
import keras.models
from ..visualization import activationModel


class TestActivationModel(unittest.TestCase):
    def setUp(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(test_dir, 'model.hdf5')
        self.model = keras.models.load_model(model_path)

    def test_activation_model(self):
        activationModel(self.model)
