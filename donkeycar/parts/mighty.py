"""MightyCamera raw body poses and a separate planar pose transform."""
from __future__ import annotations

from copy import deepcopy
import logging
import math
import threading
import time
from typing import Any, Callable, ClassVar

from donkeycar.parts.mighty_timing import MightyTiming

logger = logging.getLogger(__name__)

SDK_INSTALL_HINT = ('Mighty requires the SDK: python -m pip install '
                    'git+https://github.com/asadm/mighty-protocol.git')


class MightyLink:
    """One shared, reference-counted SDK connection per camera URL.

    The pose reader and the image camera each ``acquire`` the link for their
    URL and register their own callbacks on ``client``. The camera streams
    poses and images over a single HTTP connection, and two connections each
    run at a reduced frame rate, so every part for one URL shares this one.
    The first ``connect`` opens the stream; the last ``release`` closes it and
    forgets the link, so a later ``acquire`` starts a fresh connection.
    """
    _links: ClassVar[dict[str, MightyLink]] = {}
    _registry_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, url: str, client: Any) -> None:
        self.url = url
        self.client = client
        self.users = 0
        self.connected = False
        self.lock = threading.Lock()

    @staticmethod
    def key(url: str) -> str:
        return url.strip().rstrip('/')

    @classmethod
    def acquire(cls, url: str) -> MightyLink:
        """Return the link for ``url``, creating its client on first use."""
        key = cls.key(url)
        with cls._registry_lock:
            link = cls._links.get(key)
            if link is None:
                try:
                    from mighty_sdk import MightyClient, MightyWebDevice
                except ImportError as exc:
                    raise ImportError(SDK_INSTALL_HINT) from exc
                client = MightyClient(MightyWebDevice(base_url=key), auto_reconnect=True)
                link = cls._links[key] = cls(key, client)
            link.users += 1
            return link

    def connect(self) -> None:
        """Open the stream unless another user already has."""
        with self.lock:
            if not self.connected:
                self.client.connect()
                self.connected = True

    def release(self) -> None:
        """Drop one user; the last one disconnects and forgets the link."""
        with MightyLink._registry_lock:
            self.users -= 1
            if self.users > 0:
                return
            if MightyLink._links.get(self.url) is self:
                del MightyLink._links[self.url]
        with self.lock:
            self.connected = False
            self.client.disconnect()


class MightyPose:
    """Threaded SDK reader: raw public body pose, freshness and timing metadata.

    The raw dictionary retains the SDK's position_m, orientation_xyzw,
    timestamp_ns and confidence fields. No projection or coordinate conversion
    happens here. A fresh sample also requires a connected, tracking camera.
    """
    def __init__(self, url='http://192.168.7.1', start_vio=True,
                 max_age=0.5, high_rate_pose=False, log_directory='logs'):
        if not math.isfinite(max_age) or max_age <= 0:
            raise ValueError('Mighty max_age must be finite and positive')
        self.link = MightyLink.acquire(url)
        self.client = self.link.client
        self.released = False
        self.timing = MightyTiming(log_directory)
        self.pose_lock = threading.Lock()
        self.latest = None
        self.received_at = None
        self.state = None
        self.max_age = max_age
        self.start_vio = start_vio
        self.high_rate_pose = high_rate_pose
        self.stop = threading.Event()
        self.last_valid = None
        self.last_stats = 0.0
        # Keep the unsubscribers: the client may outlive this part when shared.
        self.unsubscribers: list[Callable[[], None]] = [
            self.client.on_pose(self.on_pose),
            self.client.on_vio_state(self.on_state),
            self.client.on_reset(self.on_reset),
            self.client.on_error(lambda error: logger.warning('Mighty: %s', error)),
        ]

    def on_pose(self, pose):
        if not isinstance(pose, dict):
            return
        # Internal camera/UPOS streams must not advance the body-pose watermark.
        if pose.get('is_public', True) and pose.get('pose_type', 'body') == 'body':
            with self.pose_lock:
                if self.timing.pose(pose):
                    self.latest = deepcopy(pose) if self.state in (None, 2) else None
                    self.received_at = time.monotonic() if self.latest is not None else None

    def on_reset(self, event):
        with self.pose_lock:
            self.state = 0
            self.latest = self.received_at = None
            self.timing.reset('camera_reset_event')
            self.timing.record('camera_reset', event=event)

    def on_state(self, state):
        with self.pose_lock:
            new_state = state.get('state')
            if new_state in (0, 1) and self.state != new_state:
                self.timing.reset('vio_off_or_initializing')
            self.state = new_state
            if self.state != 2:
                self.latest = self.received_at = None
            self.timing.record('vio_state', state=state)

    def update(self):
        try:
            self.link.connect()
            result = self.client.command('high_rate_imu', b'on' if self.high_rate_pose else b'status')
            self.timing.record('high_rate_pose', requested=self.high_rate_pose, result=result)
            logger.info('Mighty high-rate pose (requested=%s): %s', self.high_rate_pose, result)
            if self.start_vio:
                result = self.client.start_vio()
                logger.info('Mighty start_vio: %s', result)
                if not result.get('ok'):
                    logger.error('Start VIO in the Mighty visualizer to obtain a pose')
            self.stop.wait()
        finally:
            self.release()

    def run_threaded(self):
        with self.pose_lock:
            valid = bool(self.client.is_connected() and self.latest is not None
                         and self.state in (None, 2) and self.received_at is not None
                         and 0 <= time.monotonic() - self.received_at <= self.max_age)
            pose = deepcopy(self.latest) if valid else None
            timing = self.timing.snapshot()
        self.timing.record('sample', valid=valid, timing=timing)
        now = time.monotonic()
        if now - self.last_stats >= 1:
            self.last_stats = now
            self.timing.record('sdk_stats', stats=self.client.stats())
        if valid != self.last_valid:
            logger.info('Mighty pose stream: %s', 'fresh' if valid else 'unavailable; waiting for tracking')
            self.last_valid = valid
        return pose, valid, timing

    def release(self) -> None:
        """Unsubscribe and give up this part's share of the link, once."""
        with self.pose_lock:
            if self.released:
                return
            self.released = True
        for unsubscribe in self.unsubscribers:
            if callable(unsubscribe):
                unsubscribe()
        self.link.release()

    def shutdown(self):
        self.stop.set()
        try:
            self.release()
        finally:
            self.timing.close()


class MightyPoseTransform:
    """Map a raw SDK body pose to pos/x, pos/y, pos/angle and validity.

    Coordinates are local metres; angle is radians CCW from positive X.
    yaw rotates the local XY frame. heading_offset selects the vehicle-forward
    axis in the camera body XY plane (+X=0 degrees, +Y=90 degrees).
    """
    def __init__(self, yaw=0.0, heading_offset=0.0):
        if not all(math.isfinite(v) for v in (yaw, heading_offset)):
            raise ValueError('Mighty yaw and heading offset must be finite')
        self.rotation = math.radians(yaw)
        self.heading_offset = math.radians(heading_offset)

    def run(self, pose, fresh):
        invalid = (None, None, None, False)
        if not fresh or not isinstance(pose, dict):
            return invalid
        try:
            if not pose.get('is_public', True) or pose.get('pose_type', 'body') != 'body':
                return invalid
            x, y, z = map(float, pose['position_m'])
            confidence = float(pose['confidence'])
            qx, qy, qz, qw = map(float, pose['orientation_xyzw'])
            if not all(math.isfinite(v) for v in (x, y, z, confidence, qx, qy, qz, qw)) or confidence < 0.5:
                return invalid
            norm = math.hypot(qx, qy, qz, qw)
            if not math.isfinite(norm) or norm <= 1e-9:
                return invalid
            qx, qy, qz, qw = (v / norm for v in (qx, qy, qz, qw))
            fx, fy = math.cos(self.heading_offset), math.sin(self.heading_offset)
            hx = (1 - 2*(qy*qy + qz*qz))*fx + 2*(qx*qy - qz*qw)*fy
            hy = 2*(qx*qy + qz*qw)*fx + (1 - 2*(qx*qx + qz*qz))*fy
            if math.hypot(hx, hy) <= 1e-6:
                return invalid
            angle = math.atan2(hy, hx) + self.rotation
            c, s = math.cos(self.rotation), math.sin(self.rotation)
            px, py = c*x - s*y, s*x + c*y
            if not math.isfinite(px) or not math.isfinite(py):
                return invalid
            return px, py, math.atan2(math.sin(angle), math.cos(angle)), True
        except (KeyError, TypeError, ValueError, OverflowError):
            return invalid


class PoseRecordingGate:
    def run(self, recording, valid):
        return bool(recording and valid)


class PoseDriveGate:
    def run(self, mode, steering, throttle, valid):
        if mode != 'user' and not valid:
            return 0.0, 0.0
        return steering, throttle
