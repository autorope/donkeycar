# -*- coding: utf-8 -*-
import unittest
import tempfile
import os

from donkeycar.parts.datastore import Tub, TubWriter


class TestTubWriter(unittest.TestCase):

    def setUp(self):
        tempfolder = tempfile.TemporaryDirectory()
        self.path = os.path.join(tempfolder.name, 'new')
        self.inputs = ['name', 'age', 'pic']
        self.types = ['str', 'float', 'str']

    def test_tub_create(self):
        tub = TubWriter(self.path, inputs=self.inputs, types=self.types)

    def test_tub_path(self):
        tub = TubWriter(self.path, inputs=self.inputs, types=self.types)
        print(tub.types, tub.inputs)
        tub.run('will', 323, 'asdfasdf')

    def test_make_paths_absolute(self):
        tub = Tub(self.path, inputs=['file_path'], types=['image'])
        rel_file_name = 'test.jpg'
        record_dict = {'file_path': rel_file_name}
        abs_record_dict = tub.make_record_paths_absolute(record_dict)

        assert abs_record_dict['file_path'] == os.path.join(self.path, rel_file_name)