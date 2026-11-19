"""Hardware-free look-ahead steering and finite-route stop checks."""
import math
import unittest

from donkeycar.parts.open_path import LookAheadPilot, OpenPathFinish


class LookAheadTests(unittest.TestCase):
    path = [(0, i * .1) for i in range(101)]

    def test_steering_gain_scales_output_including_full_lock(self):
        for heading in (0, math.pi/2-.1):
            full = LookAheadPilot(require_heading=True, corner_min_factor=1)
            reduced = LookAheadPilot(require_heading=True, steering_gain=.75, corner_min_factor=1)
            a = full.run(self.path, 0, 0, 'local', None, True, heading)
            b = reduced.run(self.path, 0, 0, 'local', None, True, heading)
            self.assertAlmostEqual(b[0], a[0]*.75)
            self.assertEqual(a[1:], b[1:])
            self.assertLessEqual(abs(b[0]), .75)

    def test_measured_heading_updates_without_movement(self):
        pilot = LookAheadPilot(require_heading=True)
        self.assertEqual(pilot.run(self.path, 0, 0, 'local', None)[:2], (0., 0.))
        left = pilot.run(self.path, 0, 0, 'local', None, True, 0)[0]
        right = pilot.run(self.path, 0, 0, 'local', 0, True, math.pi)[0]
        self.assertLess(left, 0)
        self.assertGreater(right, 0)
        self.assertEqual(pilot.run(self.path, 0, 0, 'local', 0, True, float('nan'))[:2], (0., 0.))

    def test_recovers_from_position_and_heading_offsets(self):
        # Bicycle model: negative MM1 steering corresponds to a left turn.
        for x, heading in [(.2, math.pi/2), (-.2, math.pi/2),
                           (.1, math.pi/2-.2)]:
            controller = LookAheadPilot()
            y, index = 0., None
            for _ in range(600):
                steer, _, index = controller.run(self.path, x, y, 'local', index)
                self.assertLessEqual(abs(steer), 1)
                heading += .4/.25 * math.tan(-steer*math.radians(30)) * .05
                x += .4 * math.cos(heading) * .05
                y += .4 * math.sin(heading) * .05
                if y >= 8:
                    break
            self.assertGreaterEqual(y, 8)
            self.assertLess(abs(x), .05)

    def test_does_not_jump_to_return_leg(self):
        route = [(0, 0), (0, 1), (0, 2), (.1, 2), (.1, 1), (.1, 0)]
        pilot = LookAheadPilot()
        self.assertEqual(pilot.run(route, .1, .1, 'local', None)[2], 0)

    def test_invalid_fix_and_manual_reset(self):
        pilot = LookAheadPilot()
        self.assertEqual(pilot.run(self.path, 0, 0, 'local', None, False)[:2], (0., 0.))
        pilot.run(self.path, 0, 0, 'local', None)
        pilot.run(self.path, 0, .5, 'local', 0)
        self.assertGreater(pilot.progress, 0)
        self.assertEqual(pilot.run(self.path, 0, .5, 'user', 0), (0., 0., None))
        self.assertEqual(pilot.progress, 0)

    def test_error_stop_latches_and_freezes_progress(self):
        pilot = LookAheadPilot()
        pilot.run(self.path, 0, .5, 'local', None, True, math.pi/2)
        progress = pilot.progress
        self.assertEqual(pilot.run(self.path, 1, 1, 'local', 5, True, math.pi/2)[:2], (0., 0.))
        self.assertTrue(pilot.stopped)
        self.assertEqual(pilot.progress, progress)
        # Loading another route or regaining the path must not rearm the car.
        self.assertEqual(pilot.run([(0, 0), (0, 20)], 0, 1, 'local', None, True, math.pi/2)[:2], (0., 0.))
        pilot.run(self.path, 0, 0, 'user', None)
        self.assertGreater(pilot.run(self.path, 0, 0, 'local', None, True, math.pi/2)[1], 0)

    def test_behind_target_stop_and_manual_rearm(self):
        pilot = LookAheadPilot()
        self.assertEqual(pilot.run(self.path, 0, 0, 'local', None, True, -math.pi/2)[:2], (0., 0.))
        self.assertTrue(pilot.stopped)
        self.assertEqual(pilot.run(self.path, 0, 0, 'local', None, True, math.pi/2)[:2], (0., 0.))
        pilot.run(self.path, 0, 0, 'user', None)
        self.assertFalse(pilot.stopped)

    def test_corner_preview_reduces_throttle_before_turn(self):
        route = [(0, 0), (0, 1), (1, 1), (2, 1)]
        pilot = LookAheadPilot(lookahead=1.5)
        steer, throttle, _ = pilot.run(route, 0, 0, 'local', None, True, math.pi/2)
        self.assertGreater(abs(steer), 0)
        self.assertGreaterEqual(throttle, .5*.7)
        self.assertLess(throttle, .5)
        straight = LookAheadPilot(lookahead=1.5)
        self.assertAlmostEqual(straight.run(self.path, 0, 0, 'local', None, True, math.pi/2)[1], .5)

    def test_finish_requires_proximity_and_latches(self):
        finish = OpenPathFinish()
        self.assertEqual(finish.run(self.path, 99, 3, 11, 'local', .3, .2), (.3, .2))
        self.assertEqual(finish.run(self.path, 99, 0, 10, 'local', .3, .2), (0., 0.))
        self.assertEqual(finish.run(self.path, 99, 1, 9, 'local', .3, .2), (0., 0.))
        self.assertEqual(finish.run(self.path, 0, 0, 0, 'user', .3, .2), (.3, .2))


if __name__ == '__main__':
    unittest.main()
