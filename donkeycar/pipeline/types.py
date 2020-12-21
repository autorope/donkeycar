import os
from typing import Any, List, Optional, TypeVar, Tuple

import numpy as np
from donkeycar.config import Config
from donkeycar.parts.tub_v2 import Tub
from donkeycar.utils import load_image, load_pil_image, train_test_split
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

    def image(self, cached=True, as_nparray=True) -> np.ndarray:
        """Loads the image for you

        Args:
            cached (bool, optional): whether to cache the image. Defaults to True.
            as_nparray (bool, optional): whether to convert the image to a np array of uint8.
                                         Defaults to True. If false, returns result of Image.open()

        Returns:
            np.ndarray: [description]
        """
        if self._image is None:
            image_path = self.underlying['cam/image_array']
            full_path = os.path.join(self.base_path, 'images', image_path)

            if as_nparray:
                _image = load_image(full_path, cfg=self.config)
            else:
                # If you just want the raw Image
                _image = load_pil_image(full_path, cfg=self.config)

            if cached:
                self._image = _image
        else:
            _image = self._image
        return _image

    def __repr__(self) -> str:
        return repr(self.underlying)


class TubDataset(object):
    """
    Loads the dataset, and creates a train/test split.
    """

    def __init__(self, config: Config, tub_paths: List[str],
                 shuffle: bool = True) -> None:
        self.config = config
        self.tub_paths = tub_paths
        self.shuffle = shuffle
        self.tubs: List[Tub] = [Tub(tub_path, read_only=True)
                                for tub_path in self.tub_paths]
        self.records: List[TubRecord] = list()
        self.train_filter = getattr(config, 'TRAIN_FILTER', None)

    def train_test_split(self) -> Tuple[List[TubRecord], List[TubRecord]]:
        msg = f'Loading tubs from paths {self.tub_paths}' + f' with filter ' \
              f'{self.train_filter}' if self.train_filter else ''
        print(msg)
        self.records.clear()
        for tub in self.tubs:
            for underlying in tub:
                record = TubRecord(self.config, tub.base_path, underlying)
                if not self.train_filter or self.train_filter(record):
                    self.records.append(record)

        return train_test_split(self.records, shuffle=self.shuffle,
                                test_size=(1. - self.config.TRAIN_TEST_SPLIT))


