'''
vehicles.py

Class to pull together all parts that operate the vehicle including,
sensors, actuators, pilots and remotes.
'''

import math
import time

NaN = float('nan')
RC = 1.0 / (2.0 * math.pi * 20.0)

class PID_Info:
    P = 0.0
    I = 0.0
    D = 0.0
    desired = 0.0

class PID:
    _Kp = 0.0
    _Ki = 0.0
    _Kd = 0.0
    _integrator = 0.0
    _last_derivative = 0.0
    _last_error = 0.0
    _last_t = 0
    _imax = 5000.0
    _pid_info = PID_Info()

    def __init__(self, p, i, d):
        self._Kp = p
        self._Ki = i
        self._Kd = d

    def reset_i(self):
        self._integrator = 0
        # we use NAN (Not A Number) to indicate that the last
        # derivative value is not valid
        self._last_derivative = NaN
        self._pid_info.I = 0.0

    def get_pid(self, error, scaler = 1.0):
        error = float(error)
        tnow = time.clock() * 1000
        dt = tnow - self._last_t

        if self._last_t == 0 or dt > 1000:
            dt = 0

            # if this PID hasn't been used for a full second then zero
            # the intergator term. This prevents I buildup from a
            # previous fight mode from causing a massive return before
            # the integrator gets a chance to correct itself
            self.reset_i()

        self._last_t = tnow
        delta_time = float(dt) / 1000.0

        # Compute proportional component
        self._pid_info.P = error * self._Kp;
        output = self._pid_info.P

        # Compute derivative component if time has elapsed
        if abs(self._Kd) > 0 and dt > 0:
            derivative = 0.0

            if math.isnan(self._last_derivative):
                # we've just done a reset, suppress the first derivative
                # term as we don't want a sudden change in input to cause
                # a large D output change
                derivative = 0.0
                self._last_derivative = 0.0
            else:
                derivative = (error - self._last_error) / delta_time

            # discrete low pass filter, cuts out the
            # high frequency noise that can drive the controller crazy
            derivative = self._last_derivative + (delta_time / (RC + delta_time)) * (derivative - self._last_derivative)

            # update state
            self._last_error = error
            self._last_derivative = derivative

            # add in derivative component
            self._pid_info.D = self._Kd * derivative
            output += self._pid_info.D

        # scale the P and D components
        output *= scaler
        self._pid_info.D *= scaler
        self._pid_info.P *= scaler

        # Compute integral component if time has elapsed
        if abs(self._Ki) > 0 and dt > 0:
            self._integrator += (error * self._Ki) * scaler * delta_time

            if self._integrator < -self._imax:
                self._integrator = -self._imax
            elif self._integrator > self._imax:
                self._integrator = self._imax

            self._pid_info.I = self._integrator
            output += self._integrator

        self._pid_info.desired = output

        return output


class BaseVehicle:
    def __init__(self,
                 drive_loop_delay = .5,
                 camera=None,
                 speed = None,
                 actuator_mixer=None,
                 pilot=None,
                 remote=None):

        self.drive_loop_delay = drive_loop_delay #how long to wait between loops

        #these need tobe updated when vehicle is defined
        self.camera = camera
        self.speed = speed
        self.actuator_mixer = actuator_mixer
        self.pilot = pilot
        self.remote = remote
        self.throttle_pid = PID(0.7, 0.2, 0.2)

    def constrain(self, v, nmin, nmax):
        return max(min(nmax, v), nmin)

    def start(self):
        start_time = time.time()
        angle = 0.
        throttle = 0.
        pid_throttle = 0.

        #drive loop
        while True:
            now = time.time()
            start = now

            milliseconds = int( (now - start_time) * 1000)

            #get image array image from camera (threaded)
            img_arr = self.camera.capture_arr()
            speed = 0
            extra = None
            if self.speed:
                speed = self.speed.read_speed()
                la = self.speed.read_linaccel()
                extra = { 'speed': speed, 'linaccel': la }

            angle, throttle, drive_mode, drive = self.remote.decide_threaded(img_arr,
                                                 angle,
                                                 throttle,
                                                 milliseconds,
                                                 extra = extra)

            if drive_mode == 'local':
                angle, throttle, pilot_speed = self.pilot.decide(img_arr)

            if drive_mode == 'local_angle':
                #only update angle from local pilot
                angle, _ = self.pilot.decide(img_arr)
                pilot_speed = 'NaN'

            if drive_mode == 'user':
                self.throttle_pid.reset_i()
                pid_throttle = throttle
            else:
                if drive:
                    e = 1.5 - speed
                    pid_throttle += self.throttle_pid.get_pid(e, 5.0)
                    pid_throttle = self.constrain(pid_throttle, -500.0, 500.0)
                    throttle = pid_throttle / 1000.
                else:
                    self.throttle_pid.reset_i()
                    pid_throttle = 0.
                    throttle = 0.
                    angle = 0.

            self.actuator_mixer.update(throttle, angle)

            #print current car state
            end = time.time()
            lag = end - start
            print('\r CAR: angle: {:+04.2f}   throttle: {:+04.2f}   speed: {:+04.2f}  drive_mode: {}  drive: {}  lag: {:+04.2f}'.format(angle, throttle, speed, drive_mode, drive, lag), end='')

            time.sleep(self.drive_loop_delay)
