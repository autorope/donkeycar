import shutil
import tempfile
import unittest

from donkeycar.parts.tub_v2 import Tub


class TestTub(unittest.TestCase):

    def setUp(self):
        self._path = tempfile.mkdtemp()
        inputs = ['input']
        types = ['int']
        metadata = [("meta1", "metavalue1")]
        self.tub = Tub(self._path, inputs, types, metadata)

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

        # Note that self.tub.metadata is an array of tuples
        assert ("meta1", "metavalue1") in self.tub.metadata 

        # Note that self.tub.manifest.metadata is a dict
        assert self.tub.manifest.metadata['meta1'] == "metavalue1"

    def test_empty_tub(self):
        assert len(self.tub) == 0
        tub_iter = iter(self.tub)

        self.assertRaises(StopIteration, next, tub_iter)

    def tearDown(self):
        shutil.rmtree(self._path)


if __name__ == '__main__':
    unittest.main()
