import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from donkeycar.parts.datastore_v2 import Catalog, CatalogMetadata, Seekable


class TestCatalog(unittest.TestCase):

    def setUp(self):
        self._path = tempfile.mkdtemp()
        self._catalog_path = os.path.join(self._path, 'test.catalog')

    def test_basic_catalog_operations(self):
        catalog = Catalog(self._catalog_path)
        for i in range(0, 10):
            catalog.write_record(self._newRecord())

        self.assertEqual(os.path.exists(catalog.path.as_posix()), True)
        self.assertEqual(os.path.exists(catalog.manifest.manifest_path.as_posix()), True)

        catalog_2 = Catalog(self._catalog_path)
        catalog_2.seekable.seek_line_start(1)
        line = catalog_2.seekable.readline()
        count = 0
        while line is not None and len(line) > 0:
            print('Contents %s' % (line))
            count += 1
            line = catalog_2.seekable.readline()

        self.assertEqual(count, 10)

    def tearDown(self):
        shutil.rmtree(self._path)

    def _newRecord(self):
        record = {'at' : time.time()}
        return record

if __name__ == '__main__':
    unittest.main()
