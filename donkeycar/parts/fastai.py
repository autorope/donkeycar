"""

fastai.py

Methods to create, use, save and load pilots. Pilots contain the highlevel
logic used to determine the angle and throttle of a vehicle. Pilots can
include one or more models to help direct the vehicles motion.

"""
from abc import ABC, abstractmethod

import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional, Union, List, Sequence, Callable
from logging import getLogger

import donkeycar as dk
import torch
from donkeycar.utils import normalize_image, linear_bin
from donkeycar.pipeline.types import TubRecord, TubDataset
from donkeycar.pipeline.sequence import TubSequence
from donkeycar.parts.interpreter import FastAIInterpreter, Interpreter, KerasInterpreter

from fastai.vision.all import *
from fastai.data.transforms import *
from fastai import optimizer as fastai_optimizer
from torch.utils.data import IterableDataset, DataLoader

from torchvision import transforms

ONE_BYTE_SCALE = 1.0 / 255.0

# type of x
XY = Union[float, np.ndarray, Tuple[Union[float, np.ndarray], ...]]

logger = getLogger(__name__)
#TODO change this to use fastai Transforms
def get_default_transform():
    """
    Creates a default transform to work with torchvision models
    We use this to transform it to match imagenet mean and std

    Video transform:
    All pre-trained models expect input images normalized in the same way,
    i.e. mini-batches of 3-channel RGB videos of shape (3 x T x H x W),
    where H and W are expected to be 112, and T is a number of video frames
    in a clip. The images have to be loaded in to a range of [0, 1] and
    then normalized using mean = [0.43216, 0.394666, 0.37645] and
    std = [0.22803, 0.22145, 0.216989].
    """

    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    input_size = (224, 224)

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std)
    ])

    return transform


class FastaAiTorchTubDataset(IterableDataset):
    '''
    Loads the dataset, and creates a train/test split.
    '''

    def __init__(self, config, records: List[TubRecord], transform=None):
        """Create a FastaAi Tub Dataset

        Args:
            config (object): the configuration information
            records (List[TubRecord]): a list of tub records
            transform (function, optional): a transform to apply to the data
        """
        self.config = config

        # Handle the transforms
        if transform:
            self.transform = transform
        else:
            self.transform = get_default_transform()

        self.sequence = TubSequence(records)
        self.pipeline = self._create_pipeline()
        self.len = len(records)

    def _create_pipeline(self):
        """ This can be overridden if more complicated pipelines are
            required """

        def y_transform(record: TubRecord):
            angle: float = record.underlying['user/angle']
            throttle: float = record.underlying['user/throttle']
            predictions = torch.tensor([angle, throttle], dtype=torch.float)

            # Normalize to be between [0, 1]
            # angle and throttle are originally between [-1, 1]
            predictions = (predictions + 1) / 2
            return predictions

        def x_transform(record: TubRecord):
            # Loads the result of Image.open()
            img_arr = record.image(cached=True, as_nparray=False)
            return self.transform(img_arr)

        # Build pipeline using the transformations
        pipeline = self.sequence.build_pipeline(x_transform=x_transform,
                                                y_transform=y_transform)
        return pipeline

    def __len__(self):
        return len(self.sequence)

    def __iter__(self):
        return iter(self.pipeline)


class FastAiPilot(ABC):
    """
    Base class for Fast AI models that will provide steering and throttle to
    guide a car.
    """

    def __init__(self,
                 interpreter: Interpreter = FastAIInterpreter(),
                 input_shape: Tuple[int, ...] = (120, 160, 3)) -> None:
        self.model: Optional[Model] = None
        self.input_shape = input_shape
        self.optimizer = "adam"
        self.interpreter = interpreter
        self.interpreter.set_model(self)
        self.learner = None
        logger.info(f'Created {self} with interpreter: {interpreter}')

    def load(self, model_path):


        logger.info(f'Loading model {model_path}')
        self.interpreter.load(model_path)

    def load_weights(self, model_path: str, by_name: bool = True) -> None:
        self.interpreter.load_weights(model_path, by_name=by_name)

    def shutdown(self) -> None:
        pass

    def compile(self) -> None:
        pass

    @abstractmethod
    def create_model(self):
        pass

    def set_optimizer(self, optimizer_type: str,
                      rate: float, decay: float) -> None:
        if optimizer_type == "adam":
            optimizer = fastai_optimizer.Adam(lr=rate, wd=decay)
        elif optimizer_type == "sgd":
            optimizer = fastai_optimizer.SGD(lr=rate, wd=decay)
        elif optimizer_type == "rmsprop":
            optimizer = fastai_optimizer.RMSprop(lr=rate, wd=decay)
        else:
            raise Exception(f"Unknown optimizer type: {optimizer_type}")
        self.interpreter.set_optimizer(optimizer)

    # shape
    def get_input_shapes(self):
        return self.interpreter.get_input_shapes()

    def seq_size(self) -> int:
        return 0

    def run(self, img_arr: np.ndarray, other_arr: List[float] = None) \
            -> Tuple[Union[float, torch.tensor], ...]:
        """
        Donkeycar parts interface to run the part in the loop.

        :param img_arr:     uint8 [0,255] numpy array with image data
        :param other_arr:   numpy array of additional data to be used in the
                            pilot, like IMU array for the IMU model or a
                            state vector in the Behavioural model
        :return:            tuple of (angle, throttle)
        """
        transform = get_default_transform()
        norm_arr = transform(img_arr)
        tensor_other_array = torch.FloatTensor(other_arr) if other_arr else None
        return self.inference(norm_arr, tensor_other_array)

    def inference(self, img_arr: torch.tensor, other_arr: Optional[torch.tensor]) \
            -> Tuple[Union[float, torch.tensor], ...]:
        """ Inferencing using the interpreter
            :param img_arr:     float32 [0,1] numpy array with normalized image
                                data
            :param other_arr:   tensor array of additional data to be used in the
                                pilot, like IMU array for the IMU model or a
                                state vector in the Behavioural model
            :return:            tuple of (angle, throttle)
        """
        out = self.interpreter.predict(img_arr, other_arr)
        return self.interpreter_to_output(out)

    def inference_from_dict(self, input_dict: Dict[str, np.ndarray]) \
            -> Tuple[Union[float, np.ndarray], ...]:
        """ Inferencing using the interpreter
            :param input_dict:  input dictionary of str and np.ndarray
            :return:            typically tuple of (angle, throttle)
        """
        output = self.interpreter.predict_from_dict(input_dict)
        return self.interpreter_to_output(output)

    @abstractmethod
    def interpreter_to_output(
            self,
            interpreter_out: Sequence[Union[float, np.ndarray]]) \
            -> Tuple[Union[float, np.ndarray], ...]:
        """ Virtual method to be implemented by child classes for conversion
            :param interpreter_out:  input data
            :return:                 output values, possibly tuple of np.ndarray
        """
        pass

    def train(self,
              model_path: str,
              train_data: FastaAiTorchTubDataset,
              train_steps: int,
              batch_size: int,
              validation_data: FastaAiTorchTubDataset,
              validation_steps: int,
              epochs: int,
              verbose: int = 1,
              min_delta: float = .0005,
              patience: int = 5,
              show_plot: bool = False):
        """
        trains the model
        """
        assert isinstance(self.interpreter, FastAIInterpreter)
        model = self.interpreter.model

        dataLoader = DataLoaders.from_dsets(train_data, validation_data, bs=batch_size, shuffle=False)
        if torch.cuda.is_available():
            dataLoader.cuda()

        #dataLoaderTest = self.dataBlock.dataloaders.test_dl(validation_data, with_labels=True)
        #print(dataLoader.train[0])

        callbacks = [
            EarlyStoppingCallback(monitor='valid_loss',
                                  patience=patience,
                                  min_delta=min_delta),
            SaveModelCallback(monitor='valid_loss',
                              every_epoch=False
                              )
        ]

        self.learner = Learner(dataLoader, model, loss_func=self.loss, path=Path(model_path).parent)

        print(self.learner.summary())
        print(self.learner.loss_func)

        lr_result = self.learner.lr_find()
        suggestedLr = float(lr_result[0])

        print(f"Suggested Learning Rate {suggestedLr}")

        self.learner.fit_one_cycle(epoch, suggestedLr, cbs=callbacks)

        torch.save(self.learner.model, model_path)

        if show_plot:
            self.learner.recorder.plot_loss()
            plt.savefig(Path(model_path).with_suffix('.png'))

        history = list(map((lambda x: x.item()), self.learner.recorder.losses))

        return history

    def x_transform(self, record: Union[TubRecord, List[TubRecord]]) -> XY:
        """ Return x from record, default returns only image array"""
        assert isinstance(record, TubRecord), "TubRecord required"
        img_arr = record.image(cached=True)
        return img_arr

    def x_translate(self, x: XY) -> Dict[str, Union[float, np.ndarray]]:
        """ Translates x into dictionary where all model input layer's names
            must be matched by dictionary keys. """
        return {'img_in': x}

    def x_transform_and_process(
            self,
            record: Union[TubRecord, List[TubRecord]],
            img_processor: Callable[[np.ndarray], np.ndarray]) -> XY:
        """ Transforms the record into x for training the model to x,y, and
            applies an image augmentation. Here we assume the model only takes
            the image as input. """
        x_img = self.x_transform(record)
        # apply augmentation / normalisation
        x_process = img_processor(x_img)
        return x_process

    def y_transform(self, record: Union[TubRecord, List[TubRecord]]) -> XY:
        """ Return y from record, needs to be implemented"""
        raise NotImplementedError(f'{self} not ready yet for new training '
                                  f'pipeline')

    def y_translate(self, y: XY) -> Dict[str, Union[float, List[float]]]:
        """ Translates y into dictionary where all model output layer's names
            must be matched by dictionary keys. """
        raise NotImplementedError(f'{self} not ready yet for new training '
                                  f'pipeline')

    def output_types(self) -> Tuple[Dict[str, np.typename], ...]:
        """ Used in tf.data, assume all types are doubles"""
        # shapes = self.output_shapes()
        # types = tuple({k: tf.float64 for k in d} for d in shapes)
        return types


    def __str__(self) -> str:
        """ For printing model initialisation """
        return type(self).__name__

class FastAILinear(FastAiPilot):
    """
    The KerasLinear pilot uses one neuron to output a continuous value via
    the Keras Dense layer with linear activation. One each for steering and
    throttle. The output is not bounded.
    """

    def __init__(self,
                 interpreter: Interpreter = FastAIInterpreter(),
                 input_shape: Tuple[int, ...] = (120, 160, 3),
                 num_outputs: int = 2):
        self.num_outputs = num_outputs
        self.loss = MSELossFlat()

        super().__init__(interpreter, input_shape)

    def create_model(self):
        return Linear()

    def compile(self):
        self.optimizer = self.optimizer
        self.loss = 'mse'

    def interpreter_to_output(self, interpreter_out):
        interpreter_out = (interpreter_out * 2) - 1
        steering = interpreter_out[0]
        throttle = interpreter_out[1]
        print(steering, throttle)
        return steering, throttle

    def y_transform(self, record: Union[TubRecord, List[TubRecord]]) -> XY:
        assert isinstance(record, TubRecord), 'TubRecord expected'
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        return angle, throttle

    def y_translate(self, y: XY) -> Dict[str, Union[float, List[float]]]:
        assert isinstance(y, tuple), 'Expected tuple'
        angle, throttle = y
        return {'n_outputs0': angle, 'n_outputs1': throttle}

    def output_shapes(self):
        # need to cut off None from [None, 120, 160, 3] tensor shape
        img_shape = self.get_input_shapes()[0][1:]


class Linear(nn.Module):
    def __init__(self):
        super(Linear, self).__init__()
        self.dropout = 0.1
        # init the layers
        self.conv24 = nn.Conv2d(3, 24, kernel_size=(5, 5), stride=(2, 2))
        self.conv32 = nn.Conv2d(24, 32, kernel_size=(5, 5), stride=(2, 2))
        self.conv64_5 = nn.Conv2d(32, 64, kernel_size=(5, 5), stride=(2, 2))
        self.conv64_3 = nn.Conv2d(64, 64, kernel_size=(3, 3), stride=(1, 1))
        self.fc1 = nn.Linear(6656, 100)
        self.fc2 = nn.Linear(100, 50)
        self.drop = nn.Dropout(self.dropout)
        self.relu = nn.ReLU()
        self.output1 = nn.Linear(50, 1)
        self.output2 = nn.Linear(50, 1)
        self.flatten = nn.Flatten()

    def forward(self, x):
        x = self.relu(self.conv24(x))
        x = self.drop(x)
        x = self.relu(self.conv32(x))
        x = self.drop(x)
        x = self.relu(self.conv64_5(x))
        x = self.drop(x)
        x = self.relu(self.conv64_3(x))
        x = self.drop(x)
        x = self.relu(self.conv64_3(x))
        x = self.drop(x)
        x = self.flatten(x)
        x = self.fc1(x)
        x = self.drop(x)
        x = self.fc2(x)
        x1 = self.drop(x)
        angle = self.output1(x1)
        throttle = self.output2(x1)
        return torch.cat((angle, throttle), 1)
