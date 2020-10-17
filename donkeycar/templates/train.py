#!/usr/bin/env python3
"""
Scripts to train a keras model using tensorflow.
Basic usage should feel familiar: train.py --model models/mypilot

Usage:
    train.py [--tubs=tubs] (--model=<model>)
             [--type=(linear|inferred|latent|tensorrt_linear|tflite_linear)]
             [--latent_trained=<model>]

Options:
    -h --help              Show this screen.
"""
import datetime
import os
import random
import time
from pathlib import Path

import cv2
import numpy as np
from docopt import docopt
from PIL import Image
from tensorflow.python.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.python.keras.utils.data_utils import Sequence

import donkeycar
from donkeycar.parts.keras import KerasInferred, KerasCategorical, KerasLatent
from donkeycar.parts.tflite import keras_model_to_tflite
from donkeycar.parts.tub_v2 import Tub
from donkeycar.utils import get_model_by_type, load_image_arr, \
    train_test_split, linear_bin, normalize_image


class TubDataset(object):
    '''
    Loads the dataset, and creates a train/test split.
    '''

    def __init__(self, tub_paths, test_size=0.2, shuffle=True):
        self.tub_paths = tub_paths
        self.test_size = test_size
        self.shuffle = shuffle
        self.tubs = [Tub(tub_path, read_only=True) for tub_path in
                     self.tub_paths]
        self.records = list()

    def train_test_split(self):
        print('Loading tubs from paths %s' % (self.tub_paths))
        for tub in self.tubs:
            for record in tub:
                record['_image_base_path'] = tub.images_base_path
                self.records.append(record)

        return train_test_split(self.records, shuffle=self.shuffle, test_size=self.test_size)


class TubSequence(Sequence):
    def __init__(self, keras_model, config, records=list()):
        self.keras_model = keras_model
        self.config = config
        self.records = records
        self.batch_size = self.config.BATCH_SIZE

    def __len__(self):
        return len(self.records) // self.batch_size

    def __getitem__(self, index):
        count = 0
        records = []
        images = []
        angles = []
        throttles = []

        is_inferred = type(self.keras_model) is KerasInferred
        is_latent = type(self.keras_model) is KerasLatent

        while count < self.batch_size:
            i = (index * self.batch_size) + count
            if i >= len(self.records):
                break

            record = self.records[i]
            record = self._transform_record(record)
            records.append(record)
            count += 1

        for record in records:
            image = record['cam/image_array']
            angle = record['user/angle']
            throttle = record['user/throttle']

            images.append(image)
            angles.append(angle)
            throttles.append(throttle)

        X = np.array(images)

        if is_inferred:
            Y = np.array(angles)
        else:
            Y = [np.array(angles), np.array(throttles)]
            if is_latent and self.keras_model.decoder:
                Y.append(X)

        return X, Y

    def _transform_record(self, record):
        is_categorical = type(self.keras_model) is KerasCategorical

        for key, value in record.items():
            if key == 'cam/image_array' and isinstance(value, str):
                image_path = os.path.join(record['_image_base_path'], value)
                image = load_image_arr(image_path, self.config)
                record[key] = normalize_image(image)

            # for categorical convert to one-hot vector
            if key in ['user/angle', 'user/throttle'] and is_categorical \
                and isinstance(value, float):

                if key == 'user/angle':
                    angle = linear_bin(value, N=15, offset=1, R=2.0)
                    record[key] = angle
                elif key == 'user/throttle':
                    R = self.config.MODEL_CATEGORICAL_MAX_THROTTLE_RANGE
                    throttle = linear_bin(value, N=20, offset=0.0, R=R)
                    record[key] = throttle

        return record


class ImagePreprocessing(Sequence):
    '''
    A Sequence which wraps another Sequence with an Image Augumentation.
    '''

    def __init__(self, sequence, augmentation):
        self.sequence = sequence
        self.augumentation = augmentation

    def __len__(self):
        return len(self.sequence)

    def __getitem__(self, index):
        X, Y = self.sequence[index]
        return self.augumentation.augment_images(X), Y


def train(cfg, tub_paths, output_path, model_type):
    """
    Train the model
    """
    # convert single path into list of one element
    if type(tub_paths) is str:
        tub_paths = [tub_paths]

    if 'linear' in model_type:
        train_type = 'linear'
    else:
        train_type = model_type

    kl = get_model_by_type(train_type, cfg)
    kl.compile()

    if cfg.PRINT_MODEL_SUMMARY:
        print(kl.model.summary())

    batch_size = cfg.BATCH_SIZE
    shuffle = getattr(cfg, 'TRAIN_SHUFFLE', True)
    dataset = TubDataset(tub_paths,
                         test_size=(1. - cfg.TRAIN_TEST_SPLIT),
                         shuffle=shuffle)
    training_records, validation_records = dataset.train_test_split()
    print('Records # Training %s' % len(training_records))
    print('Records # Validation %s' % len(validation_records))

    training = TubSequence(kl, cfg, training_records)
    validation = TubSequence(kl, cfg, validation_records)
    assert len(validation) > 0, "Not enough validation data, decrease the " \
                                "batch size or add more data."

    # Setup early stoppage callbacks
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=cfg.EARLY_STOP_PATIENCE),
        ModelCheckpoint(
            filepath=output_path,
            monitor='val_loss',
            save_best_only=True,
            verbose=1,
        )
    ]

    history = kl.model.fit(
        x=training,
        steps_per_epoch=len(training),
        batch_size=batch_size,
        callbacks=callbacks,
        validation_data=validation,
        validation_steps=len(validation),
        epochs=cfg.MAX_EPOCHS,
        verbose=cfg.VERBOSE_TRAIN,
        workers=1,
        use_multiprocessing=False
    )
    return history


def main():
    args = docopt(__doc__)
    cfg = donkeycar.load_config()
    tubs = args['--tubs']
    model = args['--model']
    model_type = args['--type']
    latent_trained = args['--latent_trained']
    if latent_trained:
        cfg.LATENT_TRAINED = latent_trained
        model_type = 'latent'
    model_name, model_ext = os.path.splitext(model)
    is_tflite = model_ext == '.tflite'
    if is_tflite:
        model = f'{model_name}.h5'

    if not model_type:
        model_type = cfg.DEFAULT_MODEL_TYPE

    tubs = tubs.split(',')
    data_paths = [Path(os.path.expanduser(tub)).absolute().as_posix() for tub in tubs]
    output_path = os.path.expanduser(model)
    start = time.time()
    history = train(cfg, data_paths, output_path, model_type)
    if is_tflite:
        tflite_model_path = f'{os.path.splitext(output_path)[0]}.tflite'
        keras_model_to_tflite(output_path, tflite_model_path)
    td = datetime.timedelta(seconds=time.time() - start)
    print(f'{"-" * 40}\nTraining completed in {td}')


if __name__ == "__main__":
    main()
