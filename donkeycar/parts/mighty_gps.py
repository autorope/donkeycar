#!/usr/bin/env python3
"""Bridge Mighty SDK body poses to Donkeycar-compatible RMC GPS sentences."""
from datetime import datetime, timezone
import logging
import math
import threading
import time

import utm

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
    def __init__(self, latitude, longitude, yaw=0, max_age=0.5):
        if not all(math.isfinite(v) for v in (latitude, longitude, yaw, max_age)) or max_age <= 0:
            raise ValueError('GPS anchor and yaw must be finite; max_age must be positive')
        self.east, self.north, self.zone, self.letter = utm.from_latlon(latitude, longitude)
        self.latitude, self.longitude = latitude, longitude
        self.rotation = math.radians(yaw)
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
                self.latest = (x, y, time.monotonic()) if valid else None
            except (KeyError, TypeError, ValueError):
                self.latest = None

    def sentence(self, connected=True):
        with self.lock:
            latest = self.latest
        if not connected or latest is None or time.monotonic() - latest[2] > self.max_age:
            return rmc(self.latitude, self.longitude, False)
        x, y, _ = latest
        east = x * math.cos(self.rotation) - y * math.sin(self.rotation)
        north = x * math.sin(self.rotation) + y * math.cos(self.rotation)
        # Donkeycar converts GPS back to UTM. Inverting that same projection
        # preserves the input meter offsets instead of introducing scale error.
        lat, lon = utm.to_latlon(self.east + east, self.north + north,
                               self.zone, self.letter)
        return rmc(lat, lon)


class MightyGpsReader:
    def __init__(self, cfg):
        try:
            from mighty_sdk import MightyClient, MightyWebDevice
        except ImportError as exc:
            raise ImportError(
                'Mighty GPS requires the SDK: python -m pip install '
                'git+https://github.com/asadm/mighty-protocol.git'
            ) from exc
        self.converter = PoseGps(cfg.MIGHTY_GPS_LAT, cfg.MIGHTY_GPS_LON,
                                 cfg.MIGHTY_GPS_YAW, cfg.MIGHTY_GPS_MAX_AGE)
        self.client = MightyClient(MightyWebDevice(base_url=cfg.MIGHTY_GPS_URL),
                                  auto_reconnect=True)
        self.client.on_pose(self.converter.on_pose)
        self.client.on_vio_state(self.converter.on_state)
        self.client.on_reset(lambda _: self.converter.on_state({'state': 0}))
        self.client.on_error(lambda error: logger.warning('Mighty: %s', error))
        self.start_vio = cfg.MIGHTY_GPS_START_VIO
        self.stop = threading.Event()
        self.last_valid = None

    def update(self):
        try:
            self.client.connect()
            if self.start_vio:
                result = self.client.start_vio()
                logger.info('Mighty start_vio: %s', result)
                if not result.get('ok'):
                    logger.error('Start VIO in the Mighty visualizer to obtain a GPS fix')
            self.stop.wait()
        finally:
            self.client.disconnect()

    def run_threaded(self):
        sentence = self.converter.sentence(self.client.is_connected()).strip()
        valid = sentence.split(',')[2] == 'A'
        if valid != self.last_valid:
            logger.info('Mighty GPS fix: %s', 'valid' if valid else 'unavailable; waiting for tracking')
            self.last_valid = valid
        return [(time.time(), sentence)], valid

    def shutdown(self):
        self.stop.set()
        self.client.disconnect()


class GpsRecordingGate:
    def run(self, recording, valid):
        return bool(recording and valid)


class GpsDriveGate:
    def run(self, mode, steering, throttle, valid):
        if mode != 'user' and not valid:
            return 0.0, 0.0
        return steering, throttle
