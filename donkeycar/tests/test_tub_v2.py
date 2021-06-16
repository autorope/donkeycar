import shutil
import tempfile
import unittest

from donkeycar.parts.tub_v2 import Tub


class TestTub(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._path = tempfile.mkdtemp()
        inputs = ['input']
        types = ['int']
        cls.tub = Tub(cls._path, inputs, types)

    def test_basic_tub_operations(self):
        entries = list(self.tub)
        self.assertEqual(len(entries), 0)
        write_count = 10
        delete_indexes = [0, 8]

        records = [{'input': i} for i in range(write_count)]
        for record in records:
            self.tub.write_record(record)

        for index in delete_indexes:
            self.tub.delete_records(index)

        count = 0
        for record in self.tub:
            print('Record %s' % (record))
            count += 1

        self.assertEqual(count, (write_count - len(delete_indexes)))
        self.assertEqual(len(self.tub), (write_count - len(delete_indexes)))

    def test_delete_last_n_records(self):
        start_len = len(self.tub)
        self.tub.delete_last_n_records(2)
        self.assertEqual(start_len - 2, len(self.tub),
                         "error in deleting 2 last records")
        self.tub.delete_last_n_records(3)
        self.assertEqual(start_len - 5, len(self.tub),
                         "error in deleting 3 last records")

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._path)


if __name__ == '__main__':
    unittest.main()
