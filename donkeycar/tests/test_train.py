import tempfile
import pytest
import tarfile
import os

from donkeycar.pipeline.training import train
from donkeycar.config import Config


@pytest.fixture
def config():
    """ Config for the test with relevant parameters"""
    cfg = Config()
    cfg.BATCH_SIZE = 64
    cfg.TRAIN_TEST_SPLIT = 0.8
    cfg.IMAGE_H = 120
    cfg.IMAGE_W = 160
    cfg.IMAGE_DEPTH = 3
    cfg.PRINT_MODEL_SUMMARY = True
    cfg.EARLY_STOP_PATIENCE = 1000
    cfg.MAX_EPOCHS = 20
    cfg.MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.8
    cfg.VERBOSE_TRAIN = True
    cfg.MIN_DELTA = 0.0005
    return cfg


@pytest.fixture
def car_dir():
    """ temp directory to extract tub and run training"""
    return tempfile.mkdtemp()


@pytest.fixture
def tub_dir(car_dir):
    """ extract tub.tar.gz into temp car_dir/tub """
    tub_dir = os.path.join(car_dir, 'tub')
    this_dir = os.path.dirname(os.path.abspath(__file__))
    with tarfile.open(os.path.join(this_dir, 'tub', 'tub.tar.gz')) as file:
        file.extractall(car_dir)
    return tub_dir


@pytest.mark.parametrize('model_type_and_loss', [
                            ('linear', 0.2),
                            ('categorical', 2.0)
                            ])
def test_train(config, car_dir, tub_dir, model_type_and_loss):
    """
    Testing convergence of the linear an categorical models

    :param config:                  donkey config
    :param car_dir:                 car directory (this is a temp dir)
    :param tub_dir:                 tub directory (car_dir/tub)
    :param model_type_and_loss:     test specification of model type and loss
                                    threshold in training
    :return:                        None
    """
    model_path = os.path.join(car_dir, 'models', 'pilot.h5')
    history = train(config, tub_dir, model_path, model_type_and_loss[0])
    loss = history.history['loss']
    assert loss[-1] < model_type_and_loss[1]

