# -*- coding: utf-8 -*-
import pytest
from ..keras import KerasPilot, KerasCategorical, default_categorical
# content of ./test_smtpsimple.py
import pytest



@pytest.fixture
def pilot():
    kp = KerasPilot()
    return kp

def test_pilot_types(pilot):
    assert 1 == 1



def test_categorical():
    kc = KerasCategorical()
    assert kc.model is not None
    
def test_categorical_with_model():
    kc = KerasCategorical(default_categorical())
    assert kc.model is not None



    