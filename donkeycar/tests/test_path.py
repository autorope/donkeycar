import os
import tempfile
import unittest

from donkeycar.parts.path import CsvPath, CsvThrottlePath, CTE, OriginOffset


class TestCsvPath(unittest.TestCase):

    def test_csvpath_run(self):
        path = CsvPath()
        self.assertListEqual([(1, 2)], path.run(True, 1, 2))
        self.assertListEqual([(1, 2), (3, 4)], path.run(True, 3, 4))
        self.assertEqual(2, len(path.get_xy()))

    def test_csvpath_run_not_recording(self):
        path = CsvPath()
        self.assertListEqual([(1, 2)], path.run(True, 1, 2))
        self.assertListEqual([(1, 2)], path.run(False, 3, 4))
        self.assertListEqual([(1, 2), (3, 4)], path.run(True, 3, 4))
        self.assertEqual(2, len(path.get_xy()))

    def test_csvpath_save(self):
        path = CsvPath()
        path.run(True, 1, 2)
        path.run(True, 3, 4)
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
        path.run(True, 1, 2)
        path.run(True, 3, 4)
        path.reset()
        self.assertEqual([], path.get_xy())


    def test_csvpath_load(self):
        path = CsvPath()
        path.run(True, 1, 2)
        path.run(True, 3, 4)
        with tempfile.TemporaryDirectory() as td:
            filename = os.path.join(td, "test.csv")
            path.save(filename)
            path.reset()
            path.load(filename)
            xy = path.get_xy()
            self.assertEqual(2, len(xy))
            self.assertEqual((1, 2), xy[0])
            self.assertEqual((3, 4), xy[1])


class TestCsvThrottlePath(unittest.TestCase):
    def test_csvthrottlepath_run(self) -> None:
        path = CsvThrottlePath()
        xy, throttles = path.run(True, 1, 2, 1.0)
        self.assertListEqual([(1, 2)], xy)
        self.assertListEqual([1.0], throttles)
        xy, throttles = path.run(True, 3, 4, 0.5)
        self.assertListEqual([(1, 2), (3, 4)], xy)
        self.assertListEqual([1.0, 0.5], throttles)
        self.assertEqual(2, len(path.get_xy()))
        self.assertEqual(2, len(path.throttles))

    def test_csvthrottlepath_run_not_recording(self) -> None:
        path = CsvThrottlePath()
        xy, throttles = path.run(True, 1, 2, 1.0)
        self.assertListEqual([(1, 2)], xy)
        self.assertListEqual([1.0], throttles)
        xy, throttles = path.run(False, 3, 4, 2.0)
        self.assertListEqual([(1, 2)], xy)
        self.assertListEqual([1.0], throttles)
        xy, throttles = path.run(True, 3, 4, 0.5)
        self.assertListEqual([(1, 2), (3, 4)], xy)
        self.assertListEqual([1.0, 0.5], throttles)
        self.assertEqual(2, len(path.get_xy()))
        self.assertEqual(2, len(path.throttles))

    def test_csvthrottlepath_save(self) -> None:
        path = CsvThrottlePath()
        path.run(True, 1, 2, 1.0)
        path.run(True, 3, 4, 0.5)
        with tempfile.TemporaryDirectory() as td:
            filename = os.path.join(td, "test.csv")
            path.save(filename)
            with open(filename, "r") as testfile:
                lines = testfile.readlines()
                self.assertEqual(2, len(lines))
                self.assertEqual("1, 2, 1.0", lines[0].strip())
                self.assertEqual("3, 4, 0.5", lines[1].strip())

    def test_csvthrottlepath_reset(self) -> None:
        path = CsvThrottlePath()
        path.run(True, 1, 2, 1.0)
        path.run(True, 3, 4, 0.5)
        path.reset()
        self.assertEqual([], path.get_xy())

    def test_csvthrottlepath_load(self) -> None:
        path = CsvThrottlePath()
        path.run(True, 1, 2, 1.0)
        path.run(True, 3, 4, 0.5)
        with tempfile.TemporaryDirectory() as td:
            filename = os.path.join(td, "test.csv")
            path.save(filename)
            path.reset()
            path.load(filename)
            xy = path.get_xy()
            self.assertEqual(2, len(xy))
            self.assertEqual((1, 2), xy[0])
            self.assertEqual((3, 4), xy[1])
            self.assertListEqual([1.0, 0.5], path.throttles)


class TestCTE(unittest.TestCase):

    def test_nearest_two_pts(self):
        # path containing [(0,1)..(0,100)]
        path = []
        for i in range(100):
            path.append((0, i+1))

        cte = CTE()

        #
        # by default it finds the nearest point on the path, then
        # picks the point before it and after it as the segement.
        #
        self.assertEqual(((0, 49), (0, 51)), cte.nearest_two_pts(path, 1, 50))

        #
        # it should handle wrap around at the begining and end of path
        #
        self.assertEqual(((0, 100), (0, 2)), cte.nearest_two_pts(path, 1, 1))
        self.assertEqual(((0, 99), (0, 1)), cte.nearest_two_pts(path, 1, 100))

    def test_nearest_pt_defaults(self):
        # path containing [(0,1)..(0,100),(0,1)..(0,100)]
        path = []
        for i in range(100):
            path.append((0, i+1))
        for i in range(100):
            path.append((0, i+1))

        cte = CTE()

        #
        # by default it finds first instance of the nearest point on the path,
        #
        self.assertEqual(((0, 1), 0, 1), cte.nearest_pt(path, 1, 1))
        self.assertEqual(((0, 50), 49, 1), cte.nearest_pt(path, 1, 50))
        self.assertEqual(((0, 100), 99, 1), cte.nearest_pt(path, 1, 100))

    def test_nearest_pt_from_pt(self):
        # path containing [(0,1)..(0,100),(0,1)..(0,100)]
        path = []
        for i in range(100):
            path.append((0, i+1))
        for i in range(100):
            path.append((0, i+1))

        cte = CTE()

        #
        # should work the same as defaults; find the fist instance.
        #
        self.assertEqual(((0, 1), 0, 1), cte.nearest_pt(path, 1, 1, 0))
        self.assertEqual(((0, 50), 49, 1), cte.nearest_pt(path, 1, 50, 0))
        self.assertEqual(((0, 100), 99, 1), cte.nearest_pt(path, 1, 100, 0))

        #
        # should find the first instance from given index inclusive
        #
        self.assertEqual(((0, 1), 100, 1), cte.nearest_pt(path, 1, 1, 100))
        self.assertEqual(((0, 50), 149, 1), cte.nearest_pt(path, 1, 50, 100))
        self.assertEqual(((0, 100), 199, 1), cte.nearest_pt(path, 1, 100, 100))

        #
        # should find the first instance from given index inclusive
        # and should wrap around
        #
        self.assertEqual(((0, 1), 0, 1), cte.nearest_pt(path, 1, 1, 150))
        self.assertEqual(((0, 50), 49, 1), cte.nearest_pt(path, 1, 50, 151))
        self.assertEqual(((0, 100), 99, 1), cte.nearest_pt(path, 1, 100, 200))

    def test_nearest_pt(self):
        # path containing [(0,1)..(0,100),(0,1)..(0,100)]
        path = []
        for i in range(100):
            path.append((0, i+1))
        for i in range(100):
            path.append((0, i+1))

        cte = CTE()

        #
        # should work the same as defaults; find the fist instance.
        #
        self.assertEqual(((0, 1), 0, 1), cte.nearest_pt(path, 1, 1, 0, 200))
        self.assertEqual(((0, 50), 49, 1), cte.nearest_pt(path, 1, 50, 0, 200))
        self.assertEqual(((0, 100), 99, 1), cte.nearest_pt(path, 1, 100, 0, 200))

        #
        # stop after num_pts.
        #
        self.assertEqual(((0, 1), 0, 99), cte.nearest_pt(path, 0, 100, 0, 1))
        self.assertEqual(((0, 1), 100, 0), cte.nearest_pt(path, 0, 1, 50, 100))
        self.assertEqual(((0, 1), 0, 0), cte.nearest_pt(path, 0, 1, 150, 100))

    def test_nearest_waypoints(self):
        # path containing [(0,1)..(0,100),(0,1)..(0,100)]
        path = []
        for i in range(100):
            path.append((0, i+1))
        path += path

        cte = CTE()

        #
        # should work the same as defaults; find the fist instance.
        #
        self.assertEqual((0, 0, 1), cte.nearest_waypoints(path, 0, 1, look_ahead=1, look_behind=0))
        self.assertEqual((0, 0, 2), cte.nearest_waypoints(path, 0, 1, look_ahead=2, look_behind=0))
        self.assertEqual((0, 0, 3), cte.nearest_waypoints(path, 0, 1, look_ahead=3, look_behind=0))
        self.assertEqual((199, 0, 1), cte.nearest_waypoints(path, 0, 1, look_ahead=1, look_behind=1))
        self.assertEqual((198, 0, 2), cte.nearest_waypoints(path, 0, 1, look_ahead=2, look_behind=2))
        self.assertEqual((197, 0, 3), cte.nearest_waypoints(path, 0, 1, look_ahead=3, look_behind=3))

    def test_nearest_track(self):
        # path containing [(0,1)..(0,100),(0,1)..(0,100)]
        path = []
        for i in range(100):
            path.append((0, i+1))
        path += path

        cte = CTE()

        #
        # should work the same as defaults; find the fist instance.
        #
        self.assertEqual(((0,1), (0,2), 0), cte.nearest_track(path, 0, 1, look_ahead=1, look_behind=0))
        self.assertEqual(((0,1), (0,3), 0), cte.nearest_track(path, 0, 1, look_ahead=2, look_behind=0))
        self.assertEqual(((0,1), (0,4), 0), cte.nearest_track(path, 0, 1, look_ahead=3, look_behind=0))
        self.assertEqual(((0,100), (0,2), 0), cte.nearest_track(path, 0, 1, look_ahead=1, look_behind=1))
        self.assertEqual(((0,99), (0,3), 0), cte.nearest_track(path, 0, 1, look_ahead=2, look_behind=2))
        self.assertEqual(((0,98), (0,4), 0), cte.nearest_track(path, 0, 1, look_ahead=3, look_behind=3))


class TestOriginOffset(unittest.TestCase):
    def test_reset(self):
        oo = OriginOffset()

        #
        # origin starts at 0, 0 so point is not translated
        # the closest point index is passed through
        #
        x, y, i = oo.run(1, 2, 3)
        self.assertEqual(x, 1)
        self.assertEqual(y, 2)
        self.assertEqual(i, 3)

        x, y, i = oo.run(2, 4, 6)
        self.assertEqual(x, 2)
        self.assertEqual(y, 4)
        self.assertEqual(i, 6)

        #
        # reset the origin to (2,4)
        # this changes closes point to None
        # so that it set to default in CTE part
        #
        oo.reset_origin()
        x, y, i = oo.run(2, 4, 6)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(i, None)

        #
        # point should be offset by the origin of (2, 4)
        #
        x, y, i = oo.run(3, 6, 8)
        self.assertEqual(x, 1)
        self.assertEqual(y, 2)
        self.assertEqual(i, 8)
