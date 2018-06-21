# -*- coding: utf-8 -*-
import os
import pytest
import tempfile
import tarfile
from PIL import Image
from donkeycar.parts.datastore import Tub
from .setup import tub, tub_path, create_sample_record


def test_tub_load(tub, tub_path):
    """Tub loads from existing tub path."""
    t = Tub(tub_path)
    assert t is not None


def test_get_last_ix(tub):
    assert tub.get_last_ix() == 9


def test_get_last_ix_after_adding_new_record(tub):
    record = create_sample_record()
    tub.put_record(record)
    assert tub.get_last_ix() == 10


def test_get_last_ix_for_empty_tub(tub_path):
    inputs=['cam/image_array', 'angle', 'throttle']
    types=['image_array', 'float', 'float']
    t = Tub(tub_path, inputs=inputs, types=types)
    assert t.get_last_ix() == -1


def test_get_last_ix_for_one_record(tub_path):
    inputs=['cam/image_array', 'angle', 'throttle']
    types=['image_array', 'float', 'float']
    t = Tub(tub_path, inputs=inputs, types=types)
    record = create_sample_record()
    t.put_record(record)
    assert t.get_last_ix() == 0


def test_tub_update_df(tub):
    """ Tub updats its dataframe """
    tub.update_df()
    assert len(tub.df) == 10


def test_tub_get_df(tub):
    """ Get Tub dataframe """
    df = tub.get_df()
    assert len(df) == 10


def test_tub_add_record(tub):
    """Tub can save a record and then retrieve it."""
    rec_in = create_sample_record()
    rec_index = tub.put_record(rec_in)
    rec_out = tub.get_record(rec_index-1)
    assert rec_in.keys() == rec_out.keys()


def test_tub_get_num_records(tub):
    """ Get nbr of records in Tub """
    cnt = tub.get_num_records()
    assert cnt == 10


def test_tub_check_removes_illegal_records(tub):
    """ Get Tub dataframe """
    record = tub.get_json_record_path(tub.get_last_ix())
    with open(record, 'w') as f:
        f.write('illegal json data')
    assert tub.get_num_records() == 10

    tub.check(fix=True)
    assert tub.get_num_records() == 9


def test_tub_remove_record(tub):
    """ Remove record from tub """
    assert tub.get_num_records() == 10
    tub.remove_record(0)
    assert tub.get_num_records() == 9


def test_tub_put_image(tub_path):
    """ Add an encoded image to the tub """
    inputs = ['user/speed', 'cam/image']
    types = ['float', 'image']
    img = Image.new('RGB', (120, 160))
    t=Tub(path=tub_path, inputs=inputs, types=types)
    t.put_record({'cam/image': img, 'user/speed': 0.2, })
    assert t.get_record(t.get_last_ix())['user/speed'] == 0.2


def test_tub_put_unknown_type(tub_path):
    """ Creating a record with unknown type should fail """
    inputs = ['user/speed']
    types = ['bob']
    t=Tub(path=tub_path, inputs=inputs, types=types)
    with pytest.raises(TypeError):
        t.put_record({'user/speed': 0.2, })


def test_delete_tub(tub):
    """ Delete the tub content """
    assert tub.get_num_records() == 10
    tub.delete()
    assert tub.get_num_records() == 0


def test_get_record_gen(tub):
    """ Create a records generator and pull 20 records from it """
    records = tub.get_record_gen()
    assert len([ next(records) for x in range(20) ]) == 20


def test_get_batch_gen(tub):
    """ Create a batch generator and pull 1 batch (128) records from it """
    batches = tub.get_batch_gen()
    batch = next(batches)

    assert len( batch.keys() ) == 3
    assert len( list( batch.values() )[0] ) == 128


def test_get_train_val_gen(tub):
    """ Create training and validation generators. """
    x = ['angle', 'throttle']
    y = ['cam/image_array']
    train_gen, val_gen = tub.get_train_val_gen(x, y)

    train_batch = next(train_gen)
    assert len(train_batch)

    # X is a list of all requested features (angle & throttle)
    X = train_batch[0]
    assert len(X) == 2
    assert len(X[0]) == 128
    assert len(X[1]) == 128

    # Y is a list of all requested labels (image_array)
    Y = train_batch[1]
    assert len(Y) == 1
    assert len(Y[0]) == 128

    val_batch = next(val_gen)
    # X is a list of all requested features (angle & throttle)
    X = val_batch[0]
    assert len(X) == 2
    assert len(X[0]) == 128
    assert len(X[1]) == 128

    # Y is a list of all requested labels (image_array)
    Y = train_batch[1]
    assert len(Y) == 1
    assert len(Y[0]) == 128


def test_tar_records(tub):
    """ Tar all records in the tub """
    with tempfile.TemporaryDirectory() as tmpdirname:
        tar_path = os.path.join(tmpdirname, 'tub.tar.gz')
        tub.tar_records(tar_path)

        with tarfile.open(name=tar_path, mode='r') as t:
            assert len(t.getnames()) == 11


def test_recreating_tub(tub):
    """ Recreating a Tub should restore it to working state """
    assert tub.get_num_records() == 10
    assert tub.current_ix == 10
    assert tub.get_last_ix() == 9
    path = tub.path
    tub = None

    inputs=['cam/image_array', 'angle', 'throttle']
    types=['image_array', 'float', 'float']
    t = Tub(path, inputs=inputs, types=types)
    assert t.get_num_records() == 10
    assert t.current_ix == 10
    assert t.get_last_ix() == 9