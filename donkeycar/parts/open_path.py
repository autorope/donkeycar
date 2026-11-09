"""Endpoint handling for routes that must not wrap back to their start."""
import logging
import math

from donkeycar.parts.path import CTE


class LookAheadPilot:
    """Pure pursuit using measured heading and a bounded, forward route search.

    Mighty requires live orientation. Other sources can use movement heading;
    before movement is measurable those sources assume the first segment.
    Manual mode resets progress; callers must run this part in every mode.
    """
    def __init__(self, lookahead=0.8, wheelbase=0.25, max_angle=30,
                 steering_sign=-1.0, throttle=0.5, heading_distance=0.12,
                 require_heading=False, steering_gain=1.0, max_error=0.75,
                 corner_min_factor=0.7):
        if min(lookahead, wheelbase, max_angle, heading_distance) <= 0:
            raise ValueError('Look-ahead dimensions and angle must be positive')
        if not math.isfinite(max_error) or max_error <= 0:
            raise ValueError("Maximum path error must be positive")
        if not 0 < corner_min_factor <= 1:
            raise ValueError("Corner throttle factor must be in (0, 1]")
        self.max_error = max_error
        self.corner_min_factor = corner_min_factor
        self.stopped = False
        self.lookahead = lookahead
        self.wheelbase = wheelbase
        self.max_angle = math.radians(max_angle)
        self.sign = steering_sign
        if not math.isfinite(steering_gain) or not 0 <= steering_gain <= 1:
            raise ValueError('Steering gain must be between zero and one')
        self.steering_gain = steering_gain
        self.throttle = throttle
        self.heading_distance = heading_distance
        self.require_heading = require_heading
        self.reset()

    def reset(self):
        self.progress = 0.0
        self.anchor = None
        self.heading = None
        self.route = None

    def run(self, path, x, y, mode, closest, valid=True, heading=None):
        if mode == 'user':
            self.reset()
            self.stopped = False
            return 0.0, 0.0, None
        if self.stopped:
            return 0.0, 0.0, closest
        if not valid or path is None or len(path) < 2 or x is None or y is None:
            return 0.0, 0.0, closest
        if self.require_heading and (heading is None or not math.isfinite(heading)):
            logging.warning('LookAhead: waiting for valid Mighty orientation; stopping')
            return 0.0, 0.0, closest
        route = tuple((p[0], p[1]) for p in path)
        if route != self.route or (closest is None and self.anchor is not None):
            self.reset()
            self.route = route
        lengths = [0.0]
        for a, b in zip(route, route[1:]):
            lengths.append(lengths[-1] + math.dist(a, b))
        if lengths[-1] == 0:
            return 0.0, 0.0, None
        if heading is not None and math.isfinite(heading):
            self.heading = heading
            self.anchor = (x, y)
        elif self.heading is None:
            a, b = next((a, b) for a, b in zip(route, route[1:]) if a != b)
            self.heading = math.atan2(b[1] - a[1], b[0] - a[0])
            self.anchor = (x, y)
        dx, dy = x - self.anchor[0], y - self.anchor[1]
        if heading is None and math.hypot(dx, dy) >= self.heading_distance:
            self.heading = math.atan2(dy, dx)
            self.anchor = (x, y)

        # Project onto segments only within a short forward arc-length window.
        # Progress never moves backward or jumps to a distant return leg.
        best = None
        for i, (a, b) in enumerate(zip(route, route[1:])):
            length = lengths[i + 1] - lengths[i]
            if length == 0 or lengths[i + 1] < self.progress:
                continue
            if lengths[i] > self.progress + self.lookahead:
                break
            low = max(0.0, (self.progress - lengths[i]) / length)
            high = min(1.0, (self.progress + self.lookahead - lengths[i]) / length)
            t = max(low, min(high, ((x-a[0])*(b[0]-a[0]) + (y-a[1])*(b[1]-a[1])) / length**2))
            px, py = a[0] + t*(b[0]-a[0]), a[1] + t*(b[1]-a[1])
            candidate = (math.hypot(x-px, y-py), lengths[i] + t*length, i)
            if best is None or candidate[0] < best[0]:
                best = candidate
        if best is None:
            return 0.0, 0.0, closest
        error, candidate_progress, index = best
        if error > self.max_error:
            self.stopped = True
            logging.warning('LookAhead STOP: error=%.3f exceeds %.3f m; select manual to rearm',
                            error, self.max_error)
            return 0.0, 0.0, closest
        self.progress = candidate_progress
        target_s = min(lengths[-1], self.progress + self.lookahead)
        target = route[-1]
        for i in range(len(route)-1):
            length = lengths[i+1] - lengths[i]
            if length > 0 and lengths[i+1] >= target_s:
                t = (target_s - lengths[i]) / length
                target = (route[i][0] + t*(route[i+1][0]-route[i][0]),
                          route[i][1] + t*(route[i+1][1]-route[i][1]))
                break
        dx, dy = target[0]-x, target[1]-y
        distance_sq = dx*dx + dy*dy
        forward = math.cos(self.heading)*dx + math.sin(self.heading)*dy
        if forward < -1e-6:
            self.stopped = True
            logging.warning('LookAhead STOP: target behind car (forward=%.3f m); select manual to rearm', forward)
            return 0.0, 0.0, index
        lateral = -math.sin(self.heading)*dx + math.cos(self.heading)*dy
        angle = math.atan2(2*self.wheelbase*lateral, max(distance_sq, 1e-6))
        steering = self.steering_gain * max(-1.0, min(1.0, self.sign*angle/self.max_angle))
        # Preview the route bend even before lateral steering demand grows.
        a, b = route[index], route[index + 1]
        tangent = math.atan2(b[1]-a[1], b[0]-a[0])
        bend = math.atan2(dy, dx) - tangent
        bend = abs(math.atan2(math.sin(bend), math.cos(bend)))
        demand = min(1.0, max(bend / math.radians(30), abs(angle) / self.max_angle))
        throttle = self.throttle * (1.0 - (1.0-self.corner_min_factor)*demand)
        logging.info('LookAhead: progress=%.3f target=(%.3f, %.3f) heading=%.3f error=%.3f steer=%.3f throttle=%.3f forward=%.3f',
                     self.progress, *target, self.heading, error, steering, throttle, forward)
        return steering, throttle, index


class OpenPathCTE(CTE):
    def nearest_waypoints(self, path, x, y, look_ahead=1, look_behind=1,
                          from_pt=0, num_pts=None):
        if path is None or len(path) < 2:
            return None, None, None
        # Search the finite route. The inherited window search wraps at the end.
        _, i, _ = self.nearest_pt(path, x, y, 0, len(path))
        a = max(0, i - look_behind)
        b = min(len(path) - 1, i + look_ahead)
        if a == b:
            a, b = max(0, i - 1), min(len(path) - 1, i + 1)
        return a, i, b


class OpenPathFinish:
    def __init__(self, radius=0.25):
        self.radius = radius
        self.finished = False

    def run(self, path, closest, x, y, mode, steering, throttle):
        if mode == 'user':
            self.finished = False
            return steering, throttle
        if path is None or len(path) < 2 or closest is None:
            return 0.0, 0.0
        if not self.finished and closest >= len(path) - 3:
            end = path[-1]
            distance = math.hypot(x - end[0], y - end[1])
            if distance <= self.radius:
                self.finished = True
                logging.info('Open path finished; stopping. Select manual mode to rearm.')
        if self.finished:
            return 0.0, 0.0
        return steering, throttle
