# -*- coding: utf-8 -*- #
import pytest
import os

from donkeycar.templates.train import multi_train
from donkeycar.parts.datastore import Tub
from donkeycar.parts.simulation import SquareBoxCamera, MovingSquareTelemetry

from donkeycar.templates.train import gather_records, collate_records

#fixtures
from .setup import tub, tub_path, on_pi
from .setup import create_sample_tub

def cfg_defaults(cfg):
    cfg.MAX_EPOCHS = 1
    cfg.BATCH_SIZE = 10
    cfg.SHOW_PLOT = False
    cfg.VEBOSE_TRAIN = False
    cfg.OPTIMIZER = "adam"
    cfg.TARGET_H = cfg.IMAGE_H - cfg.ROI_CROP_TOP - cfg.ROI_CROP_BOTTOM
    cfg.TARGET_W = cfg.IMAGE_W
    cfg.TARGET_D = cfg.IMAGE_DEPTH


@pytest.mark.skipif(on_pi() == True, reason='Too slow on RPi')
def test_train_cat(tub, tub_path):
    t = Tub(tub_path)
    assert t is not None

    import donkeycar.templates.cfg_complete as cfg
    tempfolder = tub_path[:-3]
    model_path = os.path.join(tempfolder, 'test.h5')
    cfg_defaults(cfg)

    tub = tub_path
    model = model_path
    transfer = None
    model_type = "categorical"
    continuous = False
    aug = False
    multi_train(cfg, tub, model, transfer, model_type, continuous, aug)

@pytest.mark.skipif(on_pi() == True, reason='Too slow on RPi')
def test_train_linear(tub, tub_path):
    t = Tub(tub_path)
    assert t is not None

    import donkeycar.templates.cfg_complete as cfg
    tempfolder = tub_path[:-3]
    model_path = os.path.join(tempfolder, 'test.h5')
    cfg_defaults(cfg)

    tub = tub_path
    model = model_path
    transfer = None
    model_type = "linear"
    continuous = False
    aug = False
    multi_train(cfg, tub, model, transfer, model_type, continuous, aug)

'''

latent test requires opencv right now. and fails on travis ci. 
re-enable when we figure out a recipe for opencv on travis.

@pytest.mark.skipif(on_pi() == True, reason='Too slow on RPi')
def test_train_latent(tub, tub_path):
    t = Tub(tub_path)
    assert t is not None

    import donkeycar.templates.cfg_complete as cfg
    tempfolder = tub_path[:-3]
    model_path = os.path.join(tempfolder, 'test.h5')
    cfg.MAX_EPOCHS = 1
    cfg.BATCH_SIZE = 10
    cfg.SHOW_PLOT = False
    cfg.VEBOSE_TRAIN = False
    cfg.OPTIMIZER = "adam"

    tub = tub_path
    model = model_path
    transfer = None
    model_type = "latent"
    continuous = False
    aug = True
    multi_train(cfg, tub, model, transfer, model_type, continuous, aug)
'''

@pytest.mark.skipif(on_pi() == True, reason='Too slow on RPi')
def test_train_seq(tub, tub_path):
    t = Tub(tub_path)
    assert t is not None

    import donkeycar.templates.cfg_complete as cfg
    tempfolder = tub_path[:-3]
    model_path = os.path.join(tempfolder, 'test.h5')
    cfg_defaults(cfg)

    tub = tub_path
    model = model_path
    transfer = None
    model_type = "rnn"
    continuous = False
    aug = True
    multi_train(cfg, tub, model, transfer, model_type, continuous, aug)

# Helper function to calculate the Train-Test split (ratio) of a collated dataset
def calculate_TrainTestSplit(gen_records):
    train_recs = 0
    test_recs = 0
    for key in gen_records:
        if gen_records[key]['train']:
            train_recs += 1
        else:
            test_recs += 1

    total_recs = len(gen_records)
    print("Total Records: {}".format(total_recs))
    print("Train Records: {}".format(train_recs))
    print("Test Records: {}".format(test_recs))
    assert total_recs == train_recs + test_recs
    ratio = train_recs / total_recs
    print("Calculated Train-Test Split: {}".format(ratio))
    return ratio

@pytest.mark.skipif(on_pi() == True, reason='Too slow on RPi')
def test_train_TrainTestSplit_simple(tub_path):
    # Check whether the Train-Test splitting is working correctly on a dataset.
    initial_records = 100

    # Setup the test data
    t = create_sample_tub(tub_path, records=initial_records)
    assert t is not None

    # Import the configuration
    import donkeycar.templates.cfg_complete as cfg

    # Initial Setup
    opts = {'categorical' : False}
    opts['cfg'] = cfg

    orig_TRAIN_TEST_SPLIT = cfg.TRAIN_TEST_SPLIT
    records = gather_records(cfg, tub_path, opts, verbose=True)
    assert len(records) == initial_records

    # Attempt a 50:50 split
    gen_records = {}
    cfg.TRAIN_TEST_SPLIT = 0.5
    print()
    print("Testing a {} Test-Train split...".format(opts['cfg'].TRAIN_TEST_SPLIT))
    print()
    collate_records(records, gen_records, opts)
    ratio = calculate_TrainTestSplit(gen_records)
    assert ratio == cfg.TRAIN_TEST_SPLIT

    # Attempt a split based on config file (reset of the record set)
    gen_records = {}
    cfg.TRAIN_TEST_SPLIT = orig_TRAIN_TEST_SPLIT
    print()
    print("Testing a {} Test-Train split...".format(opts['cfg'].TRAIN_TEST_SPLIT))
    print()
    collate_records(records, gen_records, opts)
    ratio = calculate_TrainTestSplit(gen_records)
    assert ratio == cfg.TRAIN_TEST_SPLIT

@pytest.mark.skipif(on_pi() == True, reason='Too slow on RPi')
def test_train_TrainTestSplit_continuous(tub_path):
    # Check whether the Train-Test splitting is working correctly when a dataset is extended.
    initial_records = 100

    # Setup the test data
    t = create_sample_tub(tub_path, records=initial_records)
    assert t is not None

    # Import the configuration
    import donkeycar.templates.cfg_complete as cfg

    # Initial Setup
    gen_records = {}
    opts = {'categorical' : False}
    opts['cfg'] = cfg

    # Perform the initial split
    print()
    print("Initial split of {} records to {} Test-Train split...".format(initial_records, opts['cfg'].TRAIN_TEST_SPLIT))
    print()
    records = gather_records(cfg, tub_path, opts, verbose=True)
    assert len(records) == initial_records
    collate_records(records, gen_records, opts)
    ratio = calculate_TrainTestSplit(gen_records)
    assert ratio == cfg.TRAIN_TEST_SPLIT

    # Add some more records and recheck the ratio (only the NEW records should be added)
    additional_records = 200
    print()
    print("Added an extra {} records, aiming for overall {} Test-Train split...".format(additional_records, opts['cfg'].TRAIN_TEST_SPLIT))
    print()
    create_sample_tub(tub_path, records=additional_records)
    records = gather_records(cfg, tub_path, opts, verbose=True)
    assert len(records) == (initial_records + additional_records)
    collate_records(records, gen_records, opts)
    ratio = calculate_TrainTestSplit(gen_records)
    assert ratio == cfg.TRAIN_TEST_SPLIT
