# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.datastore import TubWriter, Tub
from donkeycar.utils import arr_to_img, img_to_arr
from PIL import ImageChops

# fixtures
from .setup import tub, tub_path


def test_tub_load(tub, tub_path):
    """Tub loads from existing tub path."""
    t = Tub(tub_path)
    assert t is not None


def test_tub_update_df(tub):
    """ Tub updates its dataframe """
    tub.update_df()
    assert len(tub.df) == 128


def test_tub_add_record(tub):
    """Tub can save a record and then retrieve it."""
    import numpy as np
    img_arr = np.zeros((120, 160))
    x = 123
    y = 90
    rec_in = {'cam/image_array': img_arr, 'user/angle': x, 'user/throttle': y}
    rec_index = tub.put_record(rec_in)
    rec_out = tub.get_record(rec_index)
    # Ignore the milliseconds key, which is added when the record is written
    if 'milliseconds' in rec_out:
        rec_out.pop('milliseconds')
    assert rec_in.keys() == rec_out.keys()


def test_tub_write_numpy(tub):
    """Tub can save a record that contains a numpy float, and retrieve it as a
        python float."""
    import numpy as np
    x = 123
    z = np.float32(11.1)
    rec_in = {'user/angle': x, 'user/throttle':z}
    rec_index = tub.put_record(rec_in)
    rec_out = tub.get_record(rec_index)
    assert type(rec_out['user/throttle']) == float


def test_tub_exclude(tub):
    """ Make sure the Tub will exclude records in the exclude set """
    ri = lambda fnm: int(os.path.basename(fnm).split('_')[1].split('.')[0])

    before = tub.gather_records()
    # Make sure we gathered records correctly
    assert len(before) == tub.get_num_records()
    tub.exclude.add(1)
    after = tub.gather_records()
    # Make sure we excluded the correct number of records
    assert len(after) == (tub.get_num_records() - 1)
    before = set([ri(f) for f in before])
    after = set([ri(f) for f in after])
    diff = before - after
    assert len(diff) == 1
    # Make sure we exclude the correct index
    assert 1 in diff


def test_tub_augment(tub):
    """Tub with augmented images which only differ slightly."""
    import numpy as np
    index = tub.get_index(shuffled=False)
    img_arr_before = [tub.get_record(ix)['cam/image_array'] for ix in index]
    tub.augment_images()
    img_arr_after = [tub.get_record(ix)['cam/image_array'] for ix in index]
    total_change = 0
    for img_arr_b, img_arr_a in zip(img_arr_before, img_arr_after):
        assert img_arr_a.shape == img_arr_b.shape, 'image size broken'
        img_a = arr_to_img(img_arr_a)
        img_b = arr_to_img(img_arr_b)
        diff = ImageChops.difference(img_a, img_b)
        diff_arr = img_to_arr(diff)
        # normalise this number
        num_pixel_channel = np.prod(diff_arr.shape)
        avg_change = diff_arr.sum() / num_pixel_channel
        # check that the augmented image is different if not totally black
        if img_arr_b.max() > 0:
            assert avg_change != 0, "Augmentation didn't do anything"
        # change per chanel can be maximally 255 in 8-bit
        total_change += avg_change

    # An average change of 1 (per 255) would be already too big on the moving
    # square images. Empirically we see changes in the order of 0.1
    assert total_change / len(img_arr_before) < 1.0, \
        'The augmented pictures differ too much.'


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
