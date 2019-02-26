# -*- coding: utf-8 -*-
import tempfile
import unittest
from donkeycar.parts.datastore import TubWriter, Tub
from donkeycar.parts.datastore import TubHandler
import os

import pytest

#fixtures
from .setup import tub, tub_path


def test_tub_load(tub, tub_path):
    """Tub loads from existing tub path."""
    t = Tub(tub_path)
    assert t is not None


def test_tub_update_df(tub):
    """ Tub updats its dataframe """
    tub.update_df()
    assert len(tub.df) == 128


def test_tub_add_record(tub):
    """Tub can save a record and then retrieve it."""
    import numpy as np
    img_arr = np.zeros((120,160))
    x=123
    y=90
    rec_in  = {'cam/image_array': img_arr, 'user/angle': x, 'user/throttle':y}
    rec_index = tub.put_record(rec_in)
    rec_out = tub.get_record(rec_index)
    # Ignore the milliseconds key, which is added when the record is written
    if 'milliseconds' in rec_out:
        rec_out.pop('milliseconds')
    assert rec_in.keys() == rec_out.keys()

class TestTubWriter(unittest.TestCase):
    def setUp(self):
        self.tempfolder = tempfile.TemporaryDirectory().name
        self.path = os.path.join(self.tempfolder, 'new')
        self.inputs = ['name', 'age', 'pic']
        self.types = ['str', 'float', 'str']

    def test_tub_create(self):
        tub = TubWriter(self.path, inputs=self.inputs, types=self.types)

    def test_tub_path(self):
        tub = TubWriter(self.path, inputs=self.inputs, types=self.types)
        tub.run('will', 323, 'asdfasdf')

    def test_make_paths_absolute(self):
        tub = Tub(self.path, inputs=['file_path'], types=['image'])
        rel_file_name = 'test.jpg'
        record_dict = {'file_path': rel_file_name}
        abs_record_dict = tub.make_record_paths_absolute(record_dict)

        assert abs_record_dict['file_path'] == os.path.join(self.path, rel_file_name)

    def test_tub_meta(self):
        meta = ["location:Here", "task:sometask"]
        tub = Tub(self.path, inputs=['file_path'], types=['image'], user_meta=meta)
        t2 = Tub(self.path)
        assert "location" in tub.meta
        assert "location" in t2.meta
        assert "sometask" == t2.meta["task"]

    def test_tub_like_driver(self):
        """ The manage.py/donkey2.py drive command creates a tub using TubHandler,
            so test that way.
        """
        os.makedirs(self.tempfolder)
        meta = ["location:Here2", "task:sometask2"]
        th = TubHandler(self.tempfolder)
        tub = th.new_tub_writer(inputs=self.inputs, types=self.types, user_meta=meta)
        t2 = Tub(tub.path)
        assert tub.meta == t2.meta
        assert tub.meta['location'] == "Here2"
        assert t2.meta['inputs'] == self.inputs
        assert t2.meta['location'] == "Here2"

