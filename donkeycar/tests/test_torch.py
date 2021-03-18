import pytest
import tarfile
import os
import numpy as np
from collections import defaultdict, namedtuple

import torch
import pytorch_lightning as pl
from donkeycar.parts.pytorch.torch_train import train
from donkeycar.parts.pytorch.torch_data import TorchTubDataModule
from donkeycar.parts.pytorch.torch_utils import get_model_by_type

from donkeycar.config import Config

Data = namedtuple('Data', ['type', 'name', 'convergence', 'pretrained'])


@pytest.fixture
def config() -> Config:
    """ Config for the test with relevant parameters"""
    cfg = Config()
    cfg.BATCH_SIZE = 2
    cfg.TRAIN_TEST_SPLIT = 0.8
    cfg.IMAGE_H = 120
    cfg.IMAGE_W = 160
    cfg.IMAGE_DEPTH = 3
    cfg.PRINT_MODEL_SUMMARY = True
    cfg.EARLY_STOP_PATIENCE = 1000
    cfg.MAX_EPOCHS = 3
    cfg.MODEL_CATEGORICAL_MAX_THROTTLE_RANGE = 0.8
    cfg.VERBOSE_TRAIN = True
    cfg.MIN_DELTA = 0.0005
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
d1 = Data(type='resnet18', name='resnet18a', convergence=1.0, pretrained=None)
test_data = [d1]


@pytest.mark.skipif("GITHUB_ACTIONS" in os.environ,
                    reason='Suppress training test in CI')
@pytest.mark.parametrize('data', test_data)
def test_train(config: Config, car_dir: str, data: Data) -> None:
    """
    Testing convergence of the linear model

    :param config:          donkey config
    :param car_dir:         car directory (this is a temp dir)
    :param data:            test case data
    :return:                None
    """
    def pilot_path(name):
        pilot_name = f'pilot_{name}.ckpt'
        return os.path.join(car_dir, 'models', pilot_name)

    tub_dir = os.path.join(car_dir, 'tub')
    loss = train(config, tub_dir, pilot_path(
        data.name), data.type, checkpoint_path=None)
    
    # check loss is converging
    assert loss[-1] < loss[0] * data.convergence


@pytest.mark.skipif("GITHUB_ACTIONS" in os.environ,
                    reason='Suppress training test in CI')
@pytest.mark.parametrize('model_type', ['resnet18'])
def test_training_pipeline(config: Config, model_type: str, car_dir: str) \
        -> None:
    """
    Testing consistency of the model interfaces and data used in training
    pipeline.

    :param config:                  donkey config
    :param model_type:              test specification of model type
    :param tub_dir:                 tub directory (car_dir/tub)
    :return:                        None
    """
    model = get_model_by_type(
        model_type, config, checkpoint_path=None)

    tub_dir = os.path.join(car_dir, 'tub')
    data_module = TorchTubDataModule(config, [tub_dir])

    if torch.cuda.is_available():
        print('Using CUDA')
        gpus = -1
    else:
        print('Not using CUDA')
        gpus = 0

    # Overfit the data
    trainer = pl.Trainer(gpus=gpus, overfit_batches=2,
                         progress_bar_refresh_rate=30, max_epochs=30)
    trainer.fit(model, data_module)
    final_loss = model.loss_history[-1]
    assert final_loss < 0.35, \
        f"final_loss of {final_loss} is too high. History: {model.loss_history}"

    # Check the batch data makes sense
    for batch in data_module.train_dataloader():
        x, y = batch
        # In order to use a model pre-trained on ImageNet, the image
        # will be re-sized to 3x224x224 regardless of what the user chooses.
        assert(x.shape == (config.BATCH_SIZE, 3, 224, 224))
        assert(y.shape == (config.BATCH_SIZE, 2))
        break

    # Check inference
    val_x, val_y = next(iter(data_module.val_dataloader()))
    output = model(val_x)
    assert(output.shape == (config.BATCH_SIZE, 2))
