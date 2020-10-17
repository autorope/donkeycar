import pytest
import tarfile
import os
from collections import namedtuple

from donkeycar.templates.train import train
from donkeycar.config import Config

Data = namedtuple('Data', ['type', 'name', 'convergence', 'pretrained'])


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
    cfg.TRAIN_SHUFFLE = False
    return cfg


@pytest.fixture(scope='session')
def car_dir(tmpdir_factory):
    """ Creating car dir with sub dirs and extracting tub """
    dir = tmpdir_factory.mktemp('mycar')
    os.mkdir(os.path.join(dir, 'models'))
    # extract tub.tar.gz into temp car_dir/tub
    this_dir = os.path.dirname(os.path.abspath(__file__))
    with tarfile.open(os.path.join(this_dir, 'tub', 'tub.tar.gz')) as file:
        file.extractall(dir)

    return dir


# define the test data
d1 = Data(type='linear', name='lin1', convergence=0.6, pretrained=None)
d2 = Data(type='categorical', name='cat1', convergence=0.85, pretrained=None)
d3 = Data(type='latent', name='lat1', convergence=0.5, pretrained=None)
d4 = Data(type='latent', name='lat2', convergence=0.5, pretrained='lat1')
test_data = [d1, d2, d3, d4]


@pytest.mark.skipif("TRAVIS" in os.environ,
                    reason='Suppress training test in CI')
@pytest.mark.parametrize('data', test_data)
def test_train(config, car_dir, data):
    """
    Testing convergence of the linear an categorical models

    :param config:          donkey config
    :param car_dir:         car directory (this is a temp dir)
    :param data:            test case data
    :return:                None
    """
    def pilot_path(name):
        pilot_name = f'pilot_{name}.h5'
        return os.path.join(car_dir, 'models', pilot_name)

    if data.pretrained:
        config.LATENT_TRAINED = pilot_path(data.pretrained)
    tub_dir = os.path.join(car_dir, 'tub')
    history = train(config, tub_dir, pilot_path(data.name), data.type)
    loss = history.history['loss']
    # check loss is converging
    assert loss[-1] < loss[0] * data.convergence

