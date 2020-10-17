import shutil
import tempfile
import unittest

from donkeycar.parts.tub_v2 import Tub


class TestTub(unittest.TestCase):

    def setUp(self):
        self._path = tempfile.mkdtemp()
        inputs = ['input', 'key']
        types = ['int', 'str']
        self.tub = Tub(self._path, inputs, types)

    def _prepare_tub(self, write_count, delete_indexes):
        records = [{'input': i, 'key': 'foo' if i < write_count // 2 else 'bar'}
                   for i in range(write_count)]
        for record in records:
            self.tub.write_record(record)

        for index in delete_indexes:
            self.tub.delete_record(index)

    def test_basic_tub_operations(self):
        entries = list(self.tub)
        self.assertEqual(len(entries), 0)
        write_count = 10
        delete_indexes = [0, 8]
        self._prepare_tub(write_count, delete_indexes)
        count = 0
        for record in self.tub:
            print('Record %s' % record)
            count += 1

        self.assertEqual(count, (write_count - len(delete_indexes)))
        self.assertEqual(len(self.tub), (write_count - len(delete_indexes)))

    def test_delete_and_resurrect_by_key(self):
        write_count = 16
        delete_indexes = [0, 5, 6, 13]
        self._prepare_tub(write_count, delete_indexes)
        orig_len = len(self.tub)
        orig_items = list(self.tub)
        deleted = self.tub.delete_records_by_value('key', 'foo')

        self.assertTrue(len(deleted) > 0, "There should be some foos to delete")
        self.assertEqual(len(self.tub), orig_len - len(deleted),
                         "Mismatching tub size")
        self.tub.undelete_records(deleted)
        self.assertEqual(len(self.tub), len(orig_items),
                         "Deleting and undeleting didn't return start tub")
        for o, n in zip(orig_items, self.tub):
            self.assertEqual(o, n, f"Undeleted items don't match original "
                                   f"items for {o} and {n}")

    def tearDown(self):
        shutil.rmtree(self._path)


if __name__ == '__main__':
    unittest.main()
