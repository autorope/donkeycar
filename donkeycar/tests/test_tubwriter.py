import shutil
import tempfile
import unittest
from random import randint

from donkeycar.parts.tub_v2 import Tub, TubWriter


class TestTub(unittest.TestCase):
    def setUp(self):
        self._path = tempfile.mkdtemp()

    def test_tubwriter_sessions(self):
        # run tubwriter multiple times on the same tub directory
        write_counts = []
        for _ in range(5):
            tub_writer = TubWriter(self._path, inputs=['input'], types=['int'])
            write_count = randint(1, 10)
            for i in range(write_count):
                tub_writer.run(i)
            tub_writer.close()
            write_counts.append(write_count)

        # Check we have good session id for all new records:
        id = 0
        total = 0
        for record in tub_writer.tub:
            print(f'Record: {record}')
            session_number = int(record['_session_id'].split('_')[1])
            self.assertEqual(session_number, id ,
                             'Session id not correctly generated')
            total += 1
            if total == write_counts[0]:
                total = 0
                id += 1
                write_counts.pop(0)

    def tearDown(self):
        shutil.rmtree(self._path)


if __name__ == '__main__':
    unittest.main()
