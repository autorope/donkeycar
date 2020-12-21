import math
import os
from typing import List, Dict, Union, Optional

from donkeycar.config import Config
from donkeycar.parts.keras import KerasPilot
from donkeycar.parts.tflite import keras_model_to_tflite
from donkeycar.pipeline.sequence import TubRecord, TubSequence, TfmIterator
from donkeycar.pipeline.types import TubDataset
from donkeycar.pipeline.augmentations import ImageAugmentation
from donkeycar.utils import get_model_by_type, normalize_image
import tensorflow as tf
import numpy as np


class BatchSequence(object):
    """
    The idea is to have a shallow sequence with types that can hydrate
    themselves to np.ndarray initially and later into the types required by
    tf.data (i.e. dictionaries or np.ndarrays).
    """
    def __init__(self,
                 model: KerasPilot,
                 config: Config,
                 records: List[TubRecord],
                 is_train: bool) -> None:
        self.model = model
        self.config = config
        self.sequence = TubSequence(records)
        self.batch_size = self.config.BATCH_SIZE
        self.is_train = is_train
        self.augmentation = ImageAugmentation(config)
        self.pipeline = self._create_pipeline()

    def __len__(self) -> int:
        return math.ceil(len(self.pipeline) / self.batch_size)

    def _create_pipeline(self) -> TfmIterator:
        """ This can be overridden if more complicated pipelines are
            required """
        # 1. Initialise TubRecord -> x, y transformations
        def get_x(record: TubRecord) -> Dict[str, Union[float, np.ndarray]]:
            """ Extracting x from record for training"""
            # this transforms the record into x for training the model to x,y
            x0 = self.model.x_transform(record)
            # for multiple input tensors the return value here is a tuple
            # where the image is in first slot otherwise x0 is the image
            x1 = x0[0] if isinstance(x0, tuple) else x0
            # apply augmentation to training data only
            x2 = self.augmentation.augment(x1) if self.is_train else x1
            # normalise image, assume other input data comes already normalised
            x3 = normalize_image(x2)
            # fill normalised image back into tuple if necessary
            x4 = (x3, ) + x0[1:] if isinstance(x0, tuple) else x3
            # convert tuple to dictionary which is understood by tf.data
            x5 = self.model.x_translate(x4)
            return x5

        def get_y(record: TubRecord) -> Dict[str, Union[float, np.ndarray]]:
            """ Extracting y from record for training """
            y0 = self.model.y_transform(record)
            y1 = self.model.y_translate(y0)
            return y1

        # 2. Build pipeline using the transformations
        pipeline = self.sequence.build_pipeline(x_transform=get_x,
                                                y_transform=get_y)
        return pipeline

    def create_tf_data(self) -> tf.data.Dataset:
        """ Assembles the tf data pipeline """
        dataset = tf.data.Dataset.from_generator(
            generator=lambda: self.pipeline,
            output_types=self.model.output_types(),
            output_shapes=self.model.output_shapes())
        return dataset.repeat().batch(self.batch_size)


def train(cfg: Config, tub_paths: str, model: str, model_type: str) -> \
        tf.keras.callbacks.History:
    """
    Train the model
    """
    model_name, model_ext = os.path.splitext(model)
    is_tflite = model_ext == '.tflite'
    if is_tflite:
        model = f'{model_name}.h5'

    if not model_type:
        model_type = cfg.DEFAULT_MODEL_TYPE

    tubs = tub_paths.split(',')
    all_tub_paths = [os.path.expanduser(tub) for tub in tubs]
    output_path = os.path.expanduser(model)
    train_type = 'linear' if 'linear' in model_type else model_type

    kl = get_model_by_type(train_type, cfg)
    if cfg.PRINT_MODEL_SUMMARY:
        print(kl.model.summary())

    dataset = TubDataset(cfg, all_tub_paths)
    training_records, validation_records = dataset.train_test_split()
    print(f'Records # Training {len(training_records)}')
    print(f'Records # Validation {len(validation_records)}')

    training_pipe = BatchSequence(kl, cfg, training_records, is_train=True)
    validation_pipe = BatchSequence(kl, cfg, validation_records, is_train=False)

    dataset_train = training_pipe.create_tf_data().prefetch(
        tf.data.experimental.AUTOTUNE)
    dataset_validate = validation_pipe.create_tf_data().prefetch(
        tf.data.experimental.AUTOTUNE)
    train_size = len(training_pipe)
    val_size = len(validation_pipe)

    assert val_size > 0, "Not enough validation data, decrease the batch " \
                         "size or add more data."

    history = kl.train(model_path=output_path,
                       train_data=dataset_train,
                       train_steps=train_size,
                       batch_size=cfg.BATCH_SIZE,
                       validation_data=dataset_validate,
                       validation_steps=val_size,
                       epochs=cfg.MAX_EPOCHS,
                       verbose=cfg.VERBOSE_TRAIN,
                       min_delta=cfg.MIN_DELTA,
                       patience=cfg.EARLY_STOP_PATIENCE)

    if is_tflite:
        tf_lite_model_path = f'{os.path.splitext(output_path)[0]}.tflite'
        keras_model_to_tflite(output_path, tf_lite_model_path)

    return history
