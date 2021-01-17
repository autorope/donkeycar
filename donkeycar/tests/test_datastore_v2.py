import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from donkeycar.parts.datastore_v2 import Manifest


class TestDatastore(unittest.TestCase):

    def setUp(self):
        self._path = tempfile.mkdtemp()

    def test_basic_datastore_operations(self):
        # 2 records per catalog entry in the manifest
        manifest = Manifest(self._path, max_len=2)
        count = 10
        for i in range(count):
            manifest.write_record(self._newRecord())

        read_records = 0
        for entry in manifest:
            print('Entry %s' % (entry))
            read_records += 1

        self.assertEqual(count, read_records)

    def test_deletion(self):
        manifest = Manifest(self._path, max_len=2)
        count = 10
        deleted = 5
        for i in range(count):
            manifest.write_record(self._newRecord())

        for i in range(deleted):
            manifest.delete_records(i)

        read_records = 0
        for entry in manifest:
            print(f'Entry {entry}')
            read_records += 1

        self.assertEqual((count - deleted), read_records)

    def test_delete_and_restore_by_set(self):
        manifest = Manifest(self._path, max_len=2)
        count = 10
        deleted = range(3, 7)
        for i in range(count):
            manifest.write_record(self._newRecord())

        manifest.delete_records(deleted)
        read_records = 0
        for entry in manifest:
            print(f'Entry {entry}')
            read_records += 1

        self.assertEqual(count - len(deleted), read_records)

        manifest.restore_records(deleted)
        read_records = 0
        for entry in manifest:
            print(f'Entry {entry}')
            read_records += 1

        self.assertEqual(count, read_records)

    def test_memory_mapped_read(self):
        manifest = Manifest(self._path, max_len=2)
        for i in range(10):
            manifest.write_record(self._newRecord())
        manifest.close()

        manifest_2 = Manifest(self._path, read_only=True)
        read_records = 0
        for _ in manifest_2:
            read_records += 1

        manifest_2.close()

        self.assertEqual(10, read_records)

    def tearDown(self):
        shutil.rmtree(self._path)

    def _newRecord(self):
        record = {'at' : time.time()}
        return record


if __name__ == '__main__':
    unittest.main()
