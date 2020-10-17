import shutil
import tempfile
import unittest

from donkeycar.parts.tub_v2 import Tub


class TestTub(unittest.TestCase):

    def setUp(self):
        self._path = tempfile.mkdtemp()
        inputs = ['input']
        types = ['int']
        self.tub = Tub(self._path, inputs, types)

    def test_basic_tub_operations(self):
        entries = list(self.tub)
        self.assertEqual(len(entries), 0)
        write_count = 10
        delete_indexes = [0, 8]

        records = [{'input': i} for i in range(write_count)]
        for record in records:
            self.tub.write_record(record)

        for index in delete_indexes:
            self.tub.delete_record(index)

        count = 0
        for record in self.tub:
            print('Record %s' % (record))
            count += 1

        self.assertEqual(count, (write_count - len(delete_indexes)))
        self.assertEqual(len(self.tub), (write_count - len(delete_indexes)))

    def tearDown(self):
        shutil.rmtree(self._path)


if __name__ == '__main__':
    unittest.main()
