import time
import unittest
from os import pipe
from typing import List, Tuple, cast

import numpy as np
from donkeycar.pipeline.sequence import SizedIterator, TubSequence
from donkeycar.pipeline.types import TubRecord, TubRecordDict


def random_records(size: int = 100) -> List[TubRecord]:
    return [random_record() for _ in range(size)]


def random_record():
    now = int(time.time())
    underlying: TubRecordDict = {
        'cam/image_array': f'/path/to/{now}.txt',
        'user/angle': np.random.uniform(0, 1.),
        'user/throttle': np.random.uniform(0, 1.),
        'user/mode': 'driving',
        'imu/acl_x': None,
        'imu/acl_y': None,
        'imu/acl_z': None,
        'imu/gyr_x': None,
        'imu/gyr_y': None,
        'imu/gyr_z': None
    }
    return TubRecord('/base', None, underlying=underlying)


size = 10


class TestPipeline(unittest.TestCase):

    def setUp(self):
        records = random_records(size=size)
        self.sequence = TubSequence(records=records)

    def test_basic_iteration(self):
        self.assertEqual(len(self.sequence), size)
        count = 0
        for record in self.sequence:
            print(f'Record {record}')
            count += 1

        self.assertEqual(count, size)

    def test_basic_map_operations(self):
        transformed = TubSequence.build_pipeline(
            self.sequence,
            x_transform=lambda record: record.underlying['user/angle'],
            y_transform=lambda record: record.underlying['user/throttle'])

        transformed_2 = TubSequence.build_pipeline(
            self.sequence,
            x_transform=lambda record: record.underlying['user/angle'] * 2,
            y_transform=lambda record: record.underlying['user/throttle'] * 2)

        self.assertEqual(len(transformed), size)
        self.assertEqual(len(transformed_2), size)

        transformed_list = list(transformed)
        transformed_list_2 = list(transformed_2)
        index = np.random.randint(0, 9)

        x1, y1 = transformed_list[index]
        x2, y2 = transformed_list_2[index]

        self.assertAlmostEqual(x1 * 2, x2)
        self.assertAlmostEqual(y1 * 2, y2)

    def test_more_map_operations(self):
        transformed = TubSequence.build_pipeline(
            self.sequence,
            x_transform=lambda record: record.underlying['user/angle'],
            y_transform=lambda record: record.underlying['user/throttle'])

        transformed_2 = TubSequence.build_pipeline(
            self.sequence,
            x_transform=lambda record: record.underlying['user/angle'] * 2,
            y_transform=lambda record: record.underlying['user/throttle'] * 2)

        transformed_3 = TubSequence.map_pipeline(
            x_transform=lambda x: x,
            y_transform=lambda y: y,
            pipeline=transformed_2
        )

        self.assertEqual(len(transformed), size)
        self.assertEqual(len(transformed_2), size)
        self.assertEqual(len(transformed_3), size)

        transformed_list = list(transformed)
        transformed_list_2 = list(transformed_3)
        index = np.random.randint(0, 9)

        x1, y1 = transformed_list[index]
        x2, y2 = transformed_list_2[index]

        self.assertAlmostEqual(x1 * 2, x2)
        self.assertAlmostEqual(y1 * 2, y2)

    def test_map_factory(self):
        transformed = TubSequence.build_pipeline(
            self.sequence,
            x_transform=lambda record: record.underlying['user/angle'],
            y_transform=lambda record: record.underlying['user/throttle'])

        transformed_2 = TubSequence.build_pipeline(
            self.sequence,
            x_transform=lambda record: record.underlying['user/angle'] * 2,
            y_transform=lambda record: record.underlying['user/throttle'] * 2)

        transformed_3 = TubSequence.map_pipeline_factory(
            x_transform=lambda x: x,
            y_transform=lambda y: y,
            factory=lambda: transformed_2
        )

        self.assertEqual(len(transformed), size)
        self.assertEqual(len(transformed_2), size)
        self.assertEqual(len(transformed_3), size)

        transformed_list = list(transformed)
        transformed_list_2 = list(transformed_3)
        index = np.random.randint(0, 9)

        x1, y1 = transformed_list[index]
        x2, y2 = transformed_list_2[index]

        self.assertAlmostEqual(x1 * 2, x2)
        self.assertAlmostEqual(y1 * 2, y2)


if __name__ == '__main__':
    unittest.main()
