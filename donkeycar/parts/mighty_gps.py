"""Mighty body pose conversion, heading and threaded GPS source."""
from datetime import datetime, timezone
import logging
import math
import threading
import time

import utm
from donkeycar.parts.mighty_timing import MightyTiming

logger = logging.getLogger(__name__)


def coordinate(value, latitude):
    absolute = abs(value)
    # Round before splitting so 59.999999999 minutes carries into degrees.
    minutes = round(absolute * 60, 8)
    degrees, minutes = divmod(minutes, 60)
    text = f"{int(degrees):0{2 if latitude else 3}d}{minutes:011.8f}"
    hemisphere = ('N' if value >= 0 else 'S') if latitude else ('E' if value >= 0 else 'W')
    return text, hemisphere


def rmc(latitude, longitude, valid=True, now=None):
    now = now or datetime.now(timezone.utc)
    lat, ns = coordinate(latitude, True)
    lon, ew = coordinate(longitude, False)
    # Speed/course are unknown; do not claim a measured speed of zero.
    body = f"GPRMC,{now:%H%M%S}.{now.microsecond // 10000:02d},{'A' if valid else 'V'},{lat},{ns},{lon},{ew},,,{now:%d%m%y},,,"
    checksum = 0
    for character in body:
        checksum ^= ord(character)
    return f"${body}*{checksum:02X}\r\n"


class PoseGps:
    def __init__(self, latitude, longitude, yaw=0, max_age=0.5, heading_offset=0):
        if not all(math.isfinite(v) for v in (latitude, longitude, yaw, max_age)) or max_age <= 0:
            raise ValueError('GPS anchor and yaw must be finite; max_age must be positive')
        self.east, self.north, self.zone, self.letter = utm.from_latlon(latitude, longitude)
        self.latitude, self.longitude = latitude, longitude
        self.rotation = math.radians(yaw)
        if not math.isfinite(heading_offset):
            raise ValueError('Heading offset must be finite')
        self.heading_offset = math.radians(heading_offset)
        self.max_age = max_age
        self.lock = threading.Lock()
        self.latest = None
        self.state = None

    def on_state(self, state):
        with self.lock:
            self.state = state['state']
            if self.state != 2:
                self.latest = None

    def on_pose(self, pose):
        with self.lock:
            try:
                x, y, z = map(float, pose['position_m'])
                confidence = float(pose['confidence'])
                valid = (pose.get('pose_type', 'body') == 'body'
                         and all(math.isfinite(v) for v in (x, y, z, confidence))
                         and confidence >= 0.5 and self.state in (None, 2))
                heading = None
                try:
                    qx, qy, qz, qw = map(float, pose['orientation_xyzw'])
                    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
                    if math.isfinite(norm) and norm > 1e-9:
                        qx, qy, qz, qw = (v/norm for v in (qx, qy, qz, qw))
                        # Project the configured body-forward axis into odom XY.
                        fx, fy = math.cos(self.heading_offset), math.sin(self.heading_offset)
                        hx = (1-2*(qy*qy+qz*qz))*fx + 2*(qx*qy-qz*qw)*fy
                        hy = 2*(qx*qy+qz*qw)*fx + (1-2*(qx*qx+qz*qz))*fy
                        if math.hypot(hx, hy) > 1e-6:
                            angle = math.atan2(hy, hx) + self.rotation
                            heading = math.atan2(math.sin(angle), math.cos(angle))
                except (KeyError, TypeError, ValueError):
                    pass  # Position can remain valid; autonomous heading cannot.
                self.latest = (x, y, time.monotonic(), heading) if valid else None
            except (KeyError, TypeError, ValueError):
                self.latest = None

    def sentence(self, connected=True):
        return self.sample(connected)[0]

    def sample(self, connected=True):
        """Return GPS sentence and heading from the same fresh pose snapshot."""
        with self.lock:
            latest = self.latest
        if not connected or latest is None or time.monotonic() - latest[2] > self.max_age:
            return rmc(self.latitude, self.longitude, False), None
        x, y, _, heading = latest
        east = x * math.cos(self.rotation) - y * math.sin(self.rotation)
        north = x * math.sin(self.rotation) + y * math.cos(self.rotation)
        # Donkeycar converts GPS back to UTM. Inverting that same projection
        # preserves the input meter offsets instead of introducing scale error.
        lat, lon = utm.to_latlon(self.east + east, self.north + north,
                               self.zone, self.letter)
        return rmc(lat, lon), heading



class MightyGpsReader:
    def __init__(self, cfg):
        from mighty_sdk import MightyClient, MightyWebDevice
        self.timing = MightyTiming()
        self.pose_lock = threading.Lock()
        self.converter = PoseGps(cfg.MIGHTY_GPS_LAT, cfg.MIGHTY_GPS_LON,
                                 cfg.MIGHTY_GPS_YAW, cfg.MIGHTY_GPS_MAX_AGE,
                                 getattr(cfg, 'MIGHTY_HEADING_OFFSET_DEGREES', 0.0))
        self.client = MightyClient(MightyWebDevice(base_url=cfg.MIGHTY_GPS_URL),
                                  auto_reconnect=True)
        self.client.on_pose(self.on_pose)
        self.client.on_vio_state(self.on_state)
        self.client.on_reset(self.on_reset)
        self.client.on_error(lambda error: logger.warning('Mighty: %s', error))
        self.start_vio = cfg.MIGHTY_GPS_START_VIO
        self.high_rate_pose = getattr(cfg, 'MIGHTY_HIGH_RATE_POSE', False)
        self.stop = threading.Event()
        self.last_valid = None
        self.last_heading_log = 0.0
        self.last_stats = 0.0

    def on_pose(self, pose):
        # Ignore internal UPOS/camera streams: only public body poses drive the car.
        if pose.get('is_public', True) and pose.get('pose_type', 'body') == 'body':
            with self.pose_lock:
                if self.timing.pose(pose):
                    self.converter.on_pose(pose)

    def on_reset(self, event):
        with self.pose_lock:
            self.converter.on_state({'state': 0})
            self.timing.reset('camera_reset_event')
            self.timing.record('camera_reset', event=event)

    def on_state(self, state):
        with self.pose_lock:
            # Reinitialize the clock watermark only on an explicit lifecycle event,
            # never on a late pose or an ordinary connection interruption.
            if state.get('state') in (0, 1) and self.converter.state != state.get('state'):
                self.timing.reset('vio_off_or_initializing')
            self.converter.on_state(state)
            self.timing.record('vio_state', state=state)

    def update(self):
        try:
            self.client.connect()
            result = self.client.command('high_rate_imu', b'on' if self.high_rate_pose else b'status')
            self.timing.record('high_rate_pose', requested=self.high_rate_pose, result=result)
            logger.info('Mighty high-rate pose (requested=%s): %s', self.high_rate_pose, result)
            if self.start_vio:
                result = self.client.start_vio()
                logger.info('Mighty start_vio: %s', result)
                if not result.get('ok'):
                    logger.error('Start VIO in the Mighty visualizer to obtain a GPS fix')
            self.stop.wait()
        finally:
            self.client.disconnect()

    def run_threaded(self):
        with self.pose_lock:
            sentence, heading = self.converter.sample(self.client.is_connected())
            timing = self.timing.snapshot()
        sentence = sentence.strip()
        valid = sentence.split(',')[2] == 'A'
        now = time.monotonic()
        self.timing.record('sample', valid=valid, heading=heading, timing=timing)
        if now - self.last_stats >= 1:
            self.last_stats = now
            self.timing.record('sdk_stats', stats=self.client.stats())
        if heading is not None and now - getattr(self, 'last_heading_log', 0.0) >= 1.0:
            logger.info('Mighty gps/heading: %.4f rad', heading)
            self.last_heading_log = now
        if valid != self.last_valid:
            logger.info('Mighty GPS fix: %s', 'valid' if valid else 'unavailable; waiting for tracking')
            self.last_valid = valid
        return [(time.time(), sentence)], valid, heading, timing

    def shutdown(self):
        self.stop.set()
        self.client.disconnect()
        self.timing.close()


class GpsRecordingGate:
    def run(self, recording, valid):
        return bool(recording and valid)


class GpsDriveGate:
    def run(self, mode, steering, throttle, valid):
        if mode != 'user' and not valid:
            return 0.0, 0.0
        return steering, throttle
