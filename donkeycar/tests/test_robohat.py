#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from donkeycar.parts.robohat import RoboHATController, RoboHATDriver
import donkeycar.templates.cfg_complete as cfg
import donkeycar as dk

def have_robohat():
    # todo - detect that we have a robohat so we can run the tests.
    return False

class TestRoboHATDriver():
    @patch('serial.Serial')
    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_trim_out_of_bound_value(self, serial):
        driver = RoboHATDriver(cfg)

        assert driver.trim_out_of_bound_value(-1.1) == -1.0
        assert driver.trim_out_of_bound_value(-0.9) == -0.9
        assert driver.trim_out_of_bound_value(0) == 0
        assert driver.trim_out_of_bound_value(0.9) == 0.9
        assert driver.trim_out_of_bound_value(1.0) == 1.0
        assert driver.trim_out_of_bound_value(1.1) == 1.0

    @patch('serial.Serial')
    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_set_pulse(self, serial):
        driver = RoboHATDriver(cfg, True)

        driver.write_pwm = MagicMock()

        # angle, throttle
        driver.set_pulse(0.0, 0.0)
        driver.write_pwm.assert_called_with(1500, 1500)

        driver.set_pulse(1.0, 0.0)
        driver.write_pwm.assert_called_with(1000, 1500)

        driver.set_pulse(0.0, 1.0)
        driver.write_pwm.assert_called_with(1500, 2000)

        driver.set_pulse(1.0, 1.0)
        driver.write_pwm.assert_called_with(1000, 2000)

        driver.set_pulse(-1.0, 0.0)
        driver.write_pwm.assert_called_with(2000, 1500)

        driver.set_pulse(0.0, -1.0)
        driver.write_pwm.assert_called_with(1500, 1000)

        driver.set_pulse(-1.0, -1.0)
        driver.write_pwm.assert_called_with(2000, 1000)

        driver.set_pulse(-2.0, -2.0)
        driver.write_pwm.assert_called_with(2000, 1000)

    @patch('serial.Serial')
    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_set_pulse_with_adjusted_throttle(self, serial):
        driver = RoboHATDriver(cfg)
        driver.MAX_FORWARD = 1800

        driver.write_pwm = MagicMock()
        driver.set_pulse(1.0, 1.0)
        driver.write_pwm.assert_called_with(1000, 1800)

        driver.set_pulse(0.0, 0.5)
        # (1800 - 1500)/ 2 + 1500 = 1650
        driver.write_pwm.assert_called_with(1500, 1650)

        # Change the STOPPED_PWM
        driver.STOPPED_PWM = 1400
        driver.set_pulse(0.0, 0.5)
        # (1800 -1400)/2 +  1400 = 1600
        driver.write_pwm.assert_called_with(1500, 1600)

        # Test Reverse
        driver.STOPPED_PWM = 1500
        driver.MAX_REVERSE = 1000
        driver.set_pulse(0.0, -0.5)
        driver.write_pwm.assert_called_with(1500, 1250)

        driver.MAX_REVERSE = 1250
        driver.set_pulse(0.0, -0.5)
        driver.write_pwm.assert_called_with(1500, 1375)


class TestRoboHATController():
    @patch('serial.Serial')
    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_controller_update(self, serial):
        controller = RoboHATController(cfg)

        # print("timeout = {}".format(seriala.timeout))
        controller.serial.readline.side_effect = [b"1500, 1500\n",
                                                  b"2000, 1500\n",
                                                  b"1600, 1600\n",
                                                  b"2000, 2000\n",
                                                  b"1000, 1000\n",
                                                  b"1200, 1200\n"]

        # 1500, 1500
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == 0

        # 2000, 1500
        controller.read_serial()
        assert controller.angle == -1.0
        assert controller.throttle == 0

        # 1600, 1600
        controller.read_serial()
        assert controller.angle == -0.2
        assert controller.throttle == 0.2

        # 2000, 2000
        controller.read_serial()
        assert controller.angle == -1.0
        assert controller.throttle == 1.0

        # 1000, 1000
        controller.read_serial()
        assert controller.angle == 1.0
        assert controller.throttle == -1.0

        # 1200, 1200
        controller.read_serial()
        assert controller.angle == 0.6
        assert controller.throttle == -0.6

    @patch('serial.Serial')
    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_controller_update_with_adjusted_mid_steering(self, serial):
        controller = RoboHATController(cfg)
        controller.STEERING_MID = 1450

        controller.serial.readline.side_effect = [b"1450, 1500\n",
                                                  b"1500, 1500\n"]

        # 1450, 1500
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == 0

        # 1500, 1500
        controller.read_serial()
        # 1450 is the mid value. So the correct angle should be (1450-1500)/ (2000-1450)
        assert controller.angle == -0.09
        assert controller.throttle == 0

    @patch('serial.Serial')
    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_controller_update_with_adjusted_max_throttle(self, serial):
        '''
        The adjusted MAX_FORWARD here should not affect the output throttle
        value.
        For example, when RC controller sending a 2000 value it means the user
        want to go full speed. The throttle value should therefore be 1.0. It is
        the RoboHATDriver responsibility to translate this 1.0 to an adjusted
        pwm value.
        '''
        controller = RoboHATController(cfg, True)
        controller.MAX_FORWARD = 1800
        controller.STOPPED_PWM = 1500

        controller.serial.readline.side_effect = [b"1500, 2000\n",
                                                  b"1500, 1500\n",
                                                  b"1500, 1750\n"]

        # 1500, 2000
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == 1.0

        # 1500, 1500
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == 0

        # 1500, 1750
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == 0.5

    @patch('serial.Serial')
    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_controller_update_with_adjusted_max_reverse(self, serial):
        controller = RoboHATController(cfg, True)
        controller.STOPPED_PWM = 1500
        controller.MAX_REVERSE = 1200

        controller.serial.readline.side_effect = [b"1500, 1000\n",
                                                  b"1500, 1250\n",
                                                  b"1500, 1000\n",
                                                  b"1500, 1250\n",
                                                  b"1500, 1500\n"]

        # 1500, 1000
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == -1.0

        # 1500, 1250
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == -0.5

        # 1500, 1000
        controller.STOPPED_PWM = 1400
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == -1.0

        # 1500, 1250
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == -0.5

        # 1500, 1500
        controller.read_serial()
        assert controller.angle == 0
        assert controller.throttle == 0


    @pytest.mark.skipif(have_robohat() == False, reason='No robohat')
    def test_controller_load_cfg(self):
        '''
        Make sure the controller load the value from config
        '''

        cfg.MM1_MAX_FORWARD = 1800
        cfg.MM1_MAX_REVERSE = 1200
        cfg.MM1_STOPPED_PWM = 1550
        cfg.MM1_STEERING_MID = 1450

        controller = RoboHATController(cfg)
        assert controller.MAX_FORWARD == 1800
        assert controller.MAX_REVERSE == 1200
        assert controller.STOPPED_PWM == 1550
        assert controller.STEERING_MID == 1450

    def test_timeout_set(self):
        assert 1 == 1
