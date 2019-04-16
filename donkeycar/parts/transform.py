# -*- coding: utf-8 -*-

import time

class Lambda:
    """
    Wraps a function into a donkey part.
    """
    def __init__(self, f):
        """
        Accepts the function to use.
        """
        self.f = f
        
    def run(self, *args, **kwargs):
        return self.f(*args, **kwargs)
    
    def shutdown(self):
        return

class TriggeredCallback:
    def __init__(self, args, func_cb):
        self.args = args
        self.func_cb = func_cb

    def run(self, trigger):
        if trigger:
            self.func_cb(self.args)

    def shutdown(self):
        return

class DelayedTrigger:
    def __init__(self, delay):
        self.ticks = 0
        self.delay = delay

    def run(self, trigger):
        if self.ticks > 0:
            self.ticks -= 1
            if self.ticks == 0:
                return True

        if trigger:
            self.ticks = self.delay

        return False

    def shutdown(self):
        return


class PIDController:
    """ Performs a PID computation and returns a control value.
        This is based on the elapsed time (dt) and the current value of the process variable
        (i.e. the thing we're measuring and trying to change).
        https://github.com/chrisspen/pid_controller/blob/master/pid_controller/pid.py
    """

    def __init__(self, p=0, i=0, d=0, debug=False):

        # initialize gains
        self.Kp = p
        self.Ki = i
        self.Kd = d

        # The value the controller is trying to get the system to achieve.
        self.target = 0

        # initialize delta t variables
        self.prev_tm = time.time()
        self.prev_err = 0
        self.error = None
        self.totalError = 0

        # initialize the output
        self.alpha = 0

        # debug flag (set to True for console output)
        self.debug = debug

    def run(self, err):
        curr_tm = time.time()

        self.difError = err - self.prev_err

        # Calculate time differential.
        dt = curr_tm - self.prev_tm

        # Initialize output variable.
        curr_alpha = 0

        # Add proportional component.
        curr_alpha += -self.Kp * err

        # Add integral component.
        curr_alpha += -self.Ki * (self.totalError * dt)

        # Add differential component (avoiding divide-by-zero).
        if dt > 0:
            curr_alpha += -self.Kd * ((self.difError) / float(dt))

        # Maintain memory for next loop.
        self.prev_tm = curr_tm
        self.prev_err = err
        self.totalError += err

        # Update the output
        self.alpha = curr_alpha

        if (self.debug):
            print('PID err value:', round(err, 4))
            print('PID output:', round(curr_alpha, 4))

        return curr_alpha


def twiddle(evaluator, tol=0.001, params=3, error_cmp=None, initial_guess=None):
    """
    A coordinate descent parameter tuning algorithm.
    https://github.com/chrisspen/pid_controller/blob/master/pid_controller/pid.py
    
    https://en.wikipedia.org/wiki/Coordinate_descent
    
    Params:
    
        evaluator := callable that will be passed a series of number parameters, which will return
            an error measure
            
        tol := tolerance threshold, the smaller the value, the greater the tuning
        
        params := the number of parameters to tune
        
        error_cmp := a callable that takes two error measures (the current and last best)
            and returns true if the first is less than the second
            
        initial_guess := parameters to begin tuning with
    """

    def _error_cmp(a, b):
        # Returns true if a is closer to zero than b.
        return abs(a) < abs(b)
        
    if error_cmp is None:
        error_cmp = _error_cmp

    if initial_guess is None:
        p = [0]*params
    else:
        p = list(initial_guess)
    dp = [1]*params
    best_err = evaluator(*p)
    steps = 0
    while sum(dp) > tol:
        steps += 1
        print('steps:', steps, 'tol:', tol, 'best error:', best_err)
        for i, _ in enumerate(p):
            
            # first try to increase param
            p[i] += dp[i]
            err = evaluator(*p)
            
            if error_cmp(err, best_err):
                # Increasing param reduced error, so record and continue to increase dp range.
                best_err = err
                dp[i] *= 1.1
            else:
                # Otherwise, increased error, so undo and try decreasing dp
                p[i] -= 2.*dp[i]
                err = evaluator(*p)
                
                if error_cmp(err, best_err):
                    # Decreasing param reduced error, so record and continue to increase dp range.
                    best_err = err
                    dp[i] *= 1.1
                    
                else:
                    # Otherwise, reset param and reduce dp range.
                    p[i] += dp[i]
                    dp[i] *= 0.9
                
    return p
