import os
import tempfile
import unittest

from donkeycar.parts.path import CsvPath, RosPath, nearest_pt_on_path


class TestCsvPath(unittest.TestCase):

    def test_csvpath_run(self):
        path = CsvPath()
        self.assertListEqual([(1, 2)], path.run(1, 2))
        self.assertListEqual([(1, 2), (3, 4)], path.run(3, 4))
        self.assertEqual(2, len(path.get_xy()))

    def test_csvpath_save(self):
        path = CsvPath()
        path.run(1, 2)
        path.run(3, 4)
        with tempfile.TemporaryDirectory() as td:
            filename = os.path.join(td, "test.csv")
            path.save(filename)
            with open(filename, "r") as testfile:
                lines = testfile.readlines()
                self.assertEqual(2, len(lines))
                self.assertEqual("1, 2", lines[0].strip())
                self.assertEqual("3, 4", lines[1].strip())

    def test_csvpath_reset(self):
        path = CsvPath()
        path.run(1, 2)
        path.run(3, 4)
        path.reset()
        self.assertEqual([], path.get_xy())


    def test_csvpath_load(self):
        path = CsvPath()
        path.run(1, 2)
        path.run(3, 4)
        with tempfile.TemporaryDirectory() as td:
            filename = os.path.join(td, "test.csv")
            path.save(filename)
            path.reset()
            path.load(filename)
            xy = path.get_xy()
            self.assertEqual(2, len(xy))
            self.assertEqual((1, 2), xy[0])
            self.assertEqual((3, 4), xy[1])


class TestNearestPtOnPath(unittest.TestCase):
    def test_nearest_pt_on_path(self):
        path = CsvPath()
        path.append(0, 1)
        path.append(1, 0)

        self.assertEqual(0, path.nearest_point(0, 0.5))
        self.assertEqual(1, path.nearest_point(0.5, 0))

        #
        # algorithm prefers the _first_ nearest point
        #
        self.assertEqual(0, path.nearest_point(0, 0, i=0))
        self.assertEqual(1, path.nearest_point(0, 0, i=1))
