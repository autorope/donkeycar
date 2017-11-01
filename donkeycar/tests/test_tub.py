# -*- coding: utf-8 -*-
import tempfile
import unittest
from donkeycar.parts.datastore import TubWriter, Tub
import os 
from .setup import create_sample_tub
import pytest

class TestMovingSquareTelemetry(unittest.TestCase):
    def setUp(self):
        tempfolder = tempfile.TemporaryDirectory()
        self.path = os.path.join(tempfolder.name, 'new')
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
        record_dict={'file_path':rel_file_name}
        abs_record_dict = tub.make_record_paths_absolute(record_dict)

        assert abs_record_dict['file_path'] == os.path.join(self.path, rel_file_name)



@pytest.fixture
def tub_path(tmpdir):
    tub_path = tmpdir.mkdir('tubs').join('tub')
    return tub_path


@pytest.fixture
def tub(tub_path):
    t = create_sample_tub(tub_path, records=10)
    return t


def test_tub_load(tub, tub_path):
    """Tub loads from existing tub path."""
    t = Tub(tub_path)
    assert t is not None


def test_tub_update_df(tub):
    """ Tub updats its dataframe """
    tub.update_df()
    assert len(tub.df) == 10

