import os
from typing import Any, List, Optional, TypeVar, Tuple

import numpy as np
from donkeycar.config import Config
from donkeycar.parts.tub_v2 import Tub
from donkeycar.utils import load_image_arr, normalize_image, train_test_split
from typing_extensions import TypedDict

X = TypeVar('X', covariant=True)

TubRecordDict = TypedDict(
    'TubRecordDict',
    {
        'cam/image_array': str,
        'user/angle': float,
        'user/throttle': float,
        'user/mode': str,
        'imu/acl_x': Optional[float],
        'imu/acl_y': Optional[float],
        'imu/acl_z': Optional[float],
        'imu/gyr_x': Optional[float],
        'imu/gyr_y': Optional[float],
        'imu/gyr_z': Optional[float],
    }
)


class TubRecord(object):
    def __init__(self, config: Config, base_path: str,
                 underlying: TubRecordDict) -> None:
        self.config = config
        self.base_path = base_path
        self.underlying = underlying
        self._image: Optional[Any] = None

    def image(self, cached=True) -> np.ndarray:
        if self._image is None:
            image_path = self.underlying['cam/image_array']
            full_path = os.path.join(self.base_path, 'images', image_path)
            _image = load_image_arr(full_path, cfg=self.config)
            if cached:
                self._image = _image
        else:
            _image = self._image
        return _image

    def __repr__(self) -> str:
        return repr(self.underlying)


class TubDataset(object):
    '''
    Loads the dataset, and creates a train/test split.
    '''

    def __init__(self, config: Config, tub_paths: List[str],
                 shuffle: bool = True) -> None:
        self.config = config
        self.tub_paths = tub_paths
        self.shuffle = shuffle
        self.tubs: List[Tub] = [Tub(tub_path, read_only=True)
                                for tub_path in self.tub_paths]
        self.records: List[TubRecord] = list()

    def train_test_split(self) -> Tuple[List[TubRecord], List[TubRecord]]:
        print(f'Loading tubs from paths {self.tub_paths}')
        self.records.clear()
        for tub in self.tubs:
            for underlying in tub:
                record = TubRecord(self.config, tub.base_path,
                                   underlying=underlying)
                self.records.append(record)

        return train_test_split(self.records, shuffle=self.shuffle,
                                test_size=(1. - self.config.TRAIN_TEST_SPLIT))
