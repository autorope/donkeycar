# -*- coding: utf-8 -*-
import unittest
import tempfile
import os

from donkeycar.parts.datastore import Tub, TubReader, TubWriter


def test_tubreader():
    with tempfile.TemporaryDirectory() as tempfolder:
        path = os.path.join(tempfolder, 'new')
        inputs = ['name', 'age', 'pic']
        types = ['str', 'float', 'str']
        writer = TubWriter(path, inputs=inputs, types=types)
        writer.run('will', 323, 'asdfasdf')
        assert writer.get_num_records() == 1

        reader = TubReader(path)
        assert reader.get_num_records() == 1

        record = reader.run('name', 'age', 'pic')
        assert set(record) == set(['will', 323, 'asdfasdf'])