import pytest
import tarfile
import os
import numpy as np
from collections import defaultdict, namedtuple
from itertools import product
from typing import Callable, List

from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.training import train, BatchSequence
from donkeycar.config import Config
from donkeycar.pipeline.types import TubDataset, TubRecord
from donkeycar.utils import get_model_by_type, normalize_image, train_test_split

Data = namedtuple('Data',
                  ['type', 'name', 'convergence', 'pretrained', 'preprocess'],
                  defaults=(None, ) * 5)


@pytest.fixture(scope='session')
def base_config() -> Config:
    """ Config for the test with relevant parameters"""
    cfg = Config()
    cfg.BATCH_SIZE = 64
    cfg.TRAIN_TEST_SPLIT = 0.8
    cfg.IMAGE_H = 120
    cfg.IMAGE_W = 160
    cfg.IMAGE_DEPTH = 3
    cfg.PRINT_MODEL_SUMMARY = True
    cfg.EARLY_STOP_PATIENCE = 1000
    cfg.MAX_EPOCHS = 6
    cfg.MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.8
    cfg.VERBOSE_TRAIN = True
    cfg.MIN_DELTA = 0.0005
    cfg.SHOW_PLOT = False
    cfg.BEHAVIOR_LIST = ['Left_Lane', "Right_Lane"]
    cfg.NUM_LOCATIONS = 3
    cfg.SEQUENCE_LENGTH = 3
    return cfg


@pytest.fixture(scope='session')
def config(base_config, car_dir) -> Config:
    cfg = base_config
    cfg.MODELS_PATH = os.path.join(car_dir, 'models')
    cfg.DATA_PATH = os.path.join(car_dir, 'tub')
    cfg.DATA_PATH_ALL = os.path.join(car_dir, 'tub_full')
    return cfg


def add_transformation_to_config(config: Config):
    config.TRANSFORMATIONS = ['CROP']
    config.ROI_CROP_TOP = 45
    config.ROI_CROP_BOTTOM = 0
    config.ROI_CROP_RIGHT = 0
    config.ROI_CROP_LEFT = 0


def add_augmentation_to_config(config: Config):
    config.AUGMENTATIONS = ['MULTIPLY', 'BLUR']


@pytest.fixture(scope='session')
def imu_fields() -> List[str]:
    return [f'imu/{prefix}_{x}' for prefix, x in product(('acl', 'gyr'), 'xyz')]


@pytest.fixture(scope='session')
def car_dir(tmpdir_factory, base_config, imu_fields) -> str:
    """ Creating car dir with sub dirs and extracting tub """
    car_dir = tmpdir_factory.mktemp('mycar')
    os.mkdir(os.path.join(car_dir, 'models'))
    # extract tub.tar.gz into car_dir/tub
    this_dir = os.path.dirname(os.path.abspath(__file__))
    with tarfile.open(os.path.join(this_dir, 'tub', 'tub.tar.gz')) as file:
        file.extractall(car_dir)
    # now create a second tub with additonal imu data
    tub_dir = os.path.join(car_dir, 'tub')
    tub = Tub(base_path=tub_dir)
    full_dir = os.path.join(car_dir, 'tub_full')
    tub_full = Tub(base_path=full_dir,
                   inputs=tub.manifest.inputs + imu_fields
                   + ['behavior/one_hot_state_array', 'localizer/location'],
                   types=tub.manifest.types + ['float'] * 6 + ['list', 'int'])
    count = 0
    for record in tub:
        t = TubRecord(base_config, tub.base_path, record)
        img = t.image()
        record['cam/image_array'] = img
        for field in imu_fields:
            record[field] = np.random.rand()
        # add behavioural input
        bhv = [1., 0.] if count < len(tub) // 2 else [0., 1.]
        record["behavior/one_hot_state_array"] = bhv
        record['localizer/location'] = 3 * count // len(tub)
        tub_full.write_record(record)
        count += 1
    return car_dir


# define the test data
d1 = Data(type='linear', name='lin1', convergence=0.6, pretrained=None)
d2 = Data(type='categorical', name='cat1', convergence=0.9, pretrained=None)
d3 = Data(type='inferred', name='inf1', convergence=0.9, pretrained=None)
d4 = Data(type='latent', name='lat1', convergence=0.5, pretrained=None)
d5 = Data(type='latent', name='lat2', convergence=0.5, pretrained='lat1')
d6 = Data(type='imu', name='imu1', convergence=0.7, pretrained=None)
d7 = Data(type='memory', name='mem1', convergence=0.6, pretrained=None)
d8 = Data(type='behavior', name='bhv1', convergence=0.9, pretrained=None)
d9 = Data(type='localizer', name='loc1', convergence=0.85, pretrained=None)
d10 = Data(type='rnn', name='rnn1', convergence=0.85, pretrained=None)
d11 = Data(type='3d', name='3d1', convergence=0.6, pretrained=None)
d12 = Data(type='linear', name='lin2', convergence=0.7, preprocess='aug')
d13 = Data(type='linear', name='lin3', convergence=0.7, preprocess='trans')

test_data = [d1, d2, d3, d6, d7, d8, d9, d10, d11, d12]
full_tub = ['imu', 'behavior', 'localizer']


@pytest.mark.skipif("GITHUB_ACTIONS" in os.environ,
                    reason='Suppress training test in CI')
@pytest.mark.parametrize('data', test_data)
def test_train(config: Config, data: Data) -> None:
    """
    Testing convergence of the linear an categorical models
    :param config:          donkey config
    :param data:            test case data
    :return:                None
    """
    def pilot_path(name):
        pilot_name = f'pilot_{name}.h5'
        return os.path.join(config.MODELS_PATH, pilot_name)

    if data.pretrained:
        config.LATENT_TRAINED = pilot_path(data.pretrained)
    tub_dir = config.DATA_PATH_ALL if data.type in full_tub else \
        config.DATA_PATH
    if data.preprocess == 'aug':
        add_augmentation_to_config(config)
    elif data.preprocess == 'trans':
        add_transformation_to_config(config)

    history = train(config, tub_dir, pilot_path(data.name), data.type)
    loss = history.history['loss']
    # check loss is converging
    assert loss[-1] < loss[0] * data.convergence


filters = [lambda r: r.underlying['user/throttle'] > 0.5,
           lambda r: r.underlying['user/angle'] < 0,
           lambda r: r.underlying['user/throttle'] < 0.6 and
                     r.underlying['user/angle'] > -0.5]
model_types = ['linear', 'categorical', 'inferred', 'imu', 'behavior',
               'localizer', 'rnn', '3d']


@pytest.mark.parametrize('model_type', model_types)
@pytest.mark.parametrize('train_filter', filters)
def test_training_pipeline(config: Config, model_type: str,
                           train_filter: Callable[[TubRecord], bool]) -> None:
    """
    Testing consistency of the model interfaces and data used in training
    pipeline.

    :param config:                  donkey config
    :param model_type:              test specification of model type
    :param train_filter:            filter for records
    :return:                        None
    """
    kl = get_model_by_type(model_type, config)
    tub_dir = config.DATA_PATH_ALL if model_type in full_tub else \
        config.DATA_PATH
    # don't shuffle so we can identify data for testing
    config.TRAIN_FILTER = train_filter
    dataset = TubDataset(config, [tub_dir], seq_size=kl.seq_size())
    training_records, validation_records = \
        train_test_split(dataset.get_records(), shuffle=False,
                         test_size=(1. - config.TRAIN_TEST_SPLIT))
    seq = BatchSequence(kl, config, training_records, True)
    data_train = seq.create_tf_data()
    num_whole_batches = len(training_records) // config.BATCH_SIZE
    # this takes all batches into one list
    tf_batch = list(data_train.take(num_whole_batches).as_numpy_iterator())
    it = iter(training_records)
    for xy_batch in tf_batch:
        # extract x and y values from records, asymmetric in x and y b/c x
        # requires image manipulations
        batch_records = [next(it) for _ in range(config.BATCH_SIZE)]
        records_x = [kl.x_translate(
            kl.x_transform_and_process(r, normalize_image)) for
            r in batch_records]
        records_y = [kl.y_translate(kl.y_transform(r)) for r in
                     batch_records]
        # from here all checks are symmetrical between x and y
        for batch, o_type, records \
                in zip(xy_batch, kl.output_types(), (records_x, records_y)):
            # check batch dictionary have expected keys
            assert batch.keys() == o_type.keys(), \
                'batch keys need to match models output types'
            # convert record values into arrays of batch size
            values = defaultdict(list)
            for r in records:
                for k, v in r.items():
                    values[k].append(v)
            # now convert arrays of floats or numpy arrays into numpy arrays
            np_dict = dict()
            for k, v in values.items():
                np_dict[k] = np.array(v)
            # compare record values with values from tf.data
            for k, v in batch.items():
                assert np.isclose(v, np_dict[k]).all()

