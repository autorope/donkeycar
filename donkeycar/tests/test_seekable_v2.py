import os
import tempfile
import unittest

from donkeycar.parts.datastore_v2 import Seekable


class TestSeekeable(unittest.TestCase):

    def setUp(self):
        self._file, self._path = tempfile.mkstemp()

    def test_offset_tracking(self):
        appendable = Seekable(self._path)
        with appendable:
            appendable.writeline('Line 1')
            appendable.writeline('Line 2')
            self.assertEqual(len(appendable.line_lengths), 2)
            appendable.seek_line_start(1)
            self.assertEqual(appendable.readline(), 'Line 1')
            appendable.seek_line_start(2)
            self.assertEqual(appendable.readline(), 'Line 2')
            appendable.seek_end_of_file()
            appendable.truncate_until_end(1)
            appendable.writeline('Line 2 Revised')
            appendable.seek_line_start(2)
            self.assertEqual(appendable.readline(), 'Line 2 Revised')

    def test_read_from_and_update(self):
        appendable = Seekable(self._path)
        with appendable:
            appendable.writeline('Line 1')
            appendable.writeline('Line 2')
            appendable.writeline('Line 3')
            # Test idempotent read
            current_offset = appendable.file.tell()
            lines = appendable.read_from(2)
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0], 'Line 2')
            self.assertEqual(lines[1], 'Line 3')
            self.assertEqual(appendable.file.tell(), current_offset)
            # Test update
            appendable.update_line(1, 'Line 1 is longer')
            lines = appendable.read_from(1)
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0], 'Line 1 is longer')
            self.assertEqual(lines[1], 'Line 2')
            self.assertEqual(lines[2], 'Line 3')

    def test_read_contents(self):
        appendable = Seekable(self._path)
        with appendable:
            appendable.writeline('Line 1')
            appendable.writeline('Line 2')
            self.assertEqual(len(appendable.line_lengths), 2)
            appendable.file.seek(0)
            appendable._read_contents()
            self.assertEqual(len(appendable.line_lengths), 2)

    def test_restore_from_index(self):
        appendable = Seekable(self._path)
        with appendable:
            appendable.writeline('Line 1')
            appendable.writeline('Line 2')
            self.assertEqual(len(appendable.line_lengths), 2)

        appendable = Seekable(self._path, line_lengths=appendable.line_lengths)
        with appendable:
            self.assertEqual(len(appendable.line_lengths), 2)
            appendable.seek_line_start(1)
            self.assertEqual(appendable.readline(), 'Line 1')
            self.assertEqual(appendable.readline(), 'Line 2')

    def tearDown(self):
        os.remove(self._path)


if __name__ == '__main__':
    unittest.main()
