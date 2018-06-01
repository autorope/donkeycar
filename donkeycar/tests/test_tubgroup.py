# -*- coding: utf-8 -*-
from donkeycar.parts.datastore import TubGroup
from .setup import tubs


def test_tubgroup_load(tubs):
    """ Load TubGroup from existing tubs dir """
    list_of_tubs = tubs[1]
    str_of_tubs = ','.join(list_of_tubs)
    t = TubGroup(str_of_tubs)
    assert t is not None


def test_tubgroup_inputs(tubs):
    """ Get TubGroup inputs """
    list_of_tubs = tubs[1]
    str_of_tubs = ','.join(list_of_tubs)
    t = TubGroup(str_of_tubs)
    assert sorted(t.inputs) == sorted(['cam/image_array', 'angle', 'throttle'])


def test_tubgroup_types(tubs):
    """ Get TubGroup types """
    list_of_tubs = tubs[1]
    str_of_tubs = ','.join(list_of_tubs)
    t = TubGroup(str_of_tubs)
    assert sorted(t.types) == sorted(['image_array', 'float', 'float'])


def test_tubgroup_get_num_tubs(tubs):
    """ Get number of tubs in TubGroup """
    list_of_tubs = tubs[1]
    str_of_tubs = ','.join(list_of_tubs)
    t = TubGroup(str_of_tubs)
    assert t.get_num_tubs() == 5


def test_tubgroup_get_num_records(tubs):
    """ Get number of records in TubGroup """
    list_of_tubs = tubs[1]
    str_of_tubs = ','.join(list_of_tubs)
    t = TubGroup(str_of_tubs)
    assert t.get_num_records() == 25
