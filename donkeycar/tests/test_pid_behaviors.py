#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from donkeycar.parts.controls.behaviors import AdjustPid
from donkeycar.parts.transform import Lambda


class FakePid:
    def __init__(self, Kp: float = 1.0, Ki: float = 0.0, Kd: float = 0.0) -> None:
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd


class TestAdjustPid(unittest.TestCase):

    def test_a_positive_step_raises_the_gain(self):
        pid = FakePid(Kp=1.0)
        AdjustPid(pid, 'Kp', 0.5).run()

        assert pid.Kp == 1.5

    def test_a_negative_step_lowers_the_gain(self):
        pid = FakePid(Kp=1.0)
        AdjustPid(pid, 'Kp', -0.5).run()

        assert pid.Kp == 0.5

    def test_the_gain_cannot_go_negative(self):
        """
        A negative gain inverts the controller: it steers away from the
        line instead of towards it, and the car leaves the track at the
        first corner.  The legacy handlers subtracted with no floor.
        """
        pid = FakePid(Kp=0.1)
        adjust = AdjustPid(pid, 'Kp', -0.5)

        adjust.run()
        assert pid.Kp == 0.0

        adjust.run()
        assert pid.Kp == 0.0

    def test_it_steps_once_per_call(self):
        pid = FakePid(Kp=1.0)
        adjust = AdjustPid(pid, 'Kp', 0.25)

        adjust.run()
        adjust.run()
        adjust.run()

        assert pid.Kp == 1.75

    def test_each_gain_is_trimmed_separately(self):
        pid = FakePid(Kp=1.0, Kd=2.0)

        AdjustPid(pid, 'Kp', 0.5).run()
        AdjustPid(pid, 'Kd', -0.5).run()

        assert pid.Kp == 1.5
        assert pid.Kd == 1.5
        assert pid.Ki == 0.0

    def test_the_floor_can_be_moved(self):
        pid = FakePid(Kp=1.0)
        AdjustPid(pid, 'Kp', -10.0, minimum=0.5).run()

        assert pid.Kp == 0.5

    def test_no_controller_is_not_a_crash(self):
        AdjustPid(None, 'Kp', 0.5).run()  # must not raise

    def test_an_unknown_gain_is_not_a_crash(self):
        pid = FakePid()
        AdjustPid(pid, 'Kx', 0.5).run()  # must not raise

        assert not hasattr(pid, 'Kx')


class TestTheRestAreLambdas(unittest.TestCase):
    """
    Saving a path, loading one, erasing one, resetting the origin, enabling
    the AI launch and stepping the behavior state are all just "call this
    when the event fires".  Lambda already does that and path_follow.py
    already uses it that way for its web buttons, so these need no parts of
    their own -- only the binding changes, in Phase 5.

    These tests exist so that claim is checked rather than assumed.
    """

    def test_lambda_calls_a_function_with_no_inputs(self):
        called = []
        Lambda(lambda: called.append(True)).run()

        assert called == [True]

    def test_lambda_can_close_over_a_template_local(self):
        """
        Which is what makes it right for these: save_path and friends close
        over the path, the config and the gps player, none of which belong
        in a general part.
        """
        saved = []
        path = ['a', 'b']

        def save_path() -> None:
            saved.append(len(path))

        Lambda(lambda: save_path()).run()
        assert saved == [2]

    def test_lambda_can_call_a_method_on_an_existing_part(self):
        """
        How EnableAiLaunch and IncrementBehaviorState are bound.
        """
        class FakeLauncher:
            def __init__(self) -> None:
                self.enabled = False

            def enable_ai_launch(self) -> None:
                self.enabled = True

        launcher = FakeLauncher()
        Lambda(lambda: launcher.enable_ai_launch()).run()

        assert launcher.enabled is True
