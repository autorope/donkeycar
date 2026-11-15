"""MightyCamera parts: shared SDK link, raw body poses, planar pose transform and images."""
from __future__ import annotations

import argparse
from copy import deepcopy
from io import BytesIO
import logging
import math
import sys
import threading
import time
from typing import Any, Callable, ClassVar, Optional, Sequence

import numpy as np
from PIL import Image

from donkeycar.parts.camera import CameraError
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


# Raw pixel formats from mighty_protocol.RAW_FORMAT that MightyCamera accepts.
RAW_GRAY8, RAW_RGB24, RAW_BGR24 = 1, 2, 3
ASPECT_NAMES = {(8, 5): '16:10'}

Size = tuple[int, int]


def aspect(width: int, height: int) -> Size:
    """Reduce a frame size to its smallest whole-number aspect ratio."""
    divisor = math.gcd(width, height)
    return width // divisor, height // divisor


def aspect_name(width: int, height: int) -> str:
    ratio = aspect(width, height)
    return ASPECT_NAMES.get(ratio, f'{ratio[0]}:{ratio[1]}')


def size_fits(width: int, height: int, native: Size) -> bool:
    """True when width x height is the camera's shape, no larger than its frames."""
    native_w, native_h = native
    return (0 < width <= native_w and 0 < height <= native_h
            and width * native_h == height * native_w)


def suggest_image_sizes(width: int, height: int, native: Size) -> list[tuple[Size, str]]:
    """Sizes to offer when width x height cannot be returned (plan D12).

    One candidate is the largest valid size whose width fits IMAGE_W, the other
    the largest whose height fits IMAGE_H, both capped at the frame size. The
    suggestion is the candidate with more pixels (the width one on a tie), or
    the smallest valid size when neither dimension admits one. The full frame
    is always offered too, unless it is already the suggestion.
    """
    native_w, native_h = native
    step_w, step_h = aspect(native_w, native_h)
    most = native_w // step_w
    candidates: list[tuple[Size, str]] = []
    k = min(width // step_w, most)
    if k >= 1:
        exact = k * step_w == width
        candidates.append(((k * step_w, k * step_h),
                           'keeps your width' if exact else 'the largest that fits your width'))
    k = min(height // step_h, most)
    if k >= 1:
        exact = k * step_h == height
        candidates.append(((k * step_w, k * step_h),
                           'keeps your height' if exact else 'the largest that fits your height'))
    if not candidates:
        candidates.append(((step_w, step_h), 'the smallest size'))
    best = max(candidates, key=lambda c: c[0][0] * c[0][1])
    if best[0] == native:
        return [(native, 'the full frame')]
    return [best, (native, 'the full frame')]


def image_size_error(width: int, height: int, native: Size) -> Optional[str]:
    """None if the camera can return width x height, else the myconfig.py fix."""
    if size_fits(width, height, native):
        return None
    native_w, native_h = native
    if width <= 0 or height <= 0:
        why = 'because it is not a positive size'
    elif width * native_h != height * native_w:
        why = 'without stretching'
    else:
        why = "because it is larger than the camera's frames"
    ratio = aspect_name(native_w, native_h)
    fixes = ', or '.join(f'IMAGE_W = {w} and IMAGE_H = {h} ({reason})'
                         for (w, h), reason in suggest_image_sizes(width, height, native))
    return (f'MightyCamera cannot return IMAGE_W={width}, IMAGE_H={height} {why}: '
            f'the camera sends {native_w}x{native_h} ({ratio}). '
            f'In myconfig.py set {fixes}. '
            f'Any {ratio} size up to {native_w}x{native_h} works.')


def framerate_error(requested: float, measured: float) -> Optional[str]:
    """None if the camera keeps up with CAMERA_FRAMERATE, else the fix (plan D14).

    The camera sets its own rate, so the most donkeycar can ask for is the
    measured rate rounded down to a whole frame per second.
    """
    supported = math.floor(measured)
    if requested <= supported:
        return None
    if supported < 1:
        return (f'MightyCamera is sending only {measured:.1f} fps, too slow for '
                f'CAMERA_FRAMERATE = {requested:g}. Check the camera connection; '
                f'images should arrive at about 15-18 fps.')
    return (f'MightyCamera cannot deliver CAMERA_FRAMERATE = {requested:g}: the camera is '
            f'sending {measured:.1f} fps. The camera sets its own rate, and it drops to '
            f'about 15 fps while VIO runs. In myconfig.py set '
            f'CAMERA_FRAMERATE = {supported}, or anything lower.')


def primary_image(image: Any) -> Optional[dict[str, Any]]:
    """The mono/primary member of an SDK image event, as the SDK selects it.

    Dropped frames and loop-closure reference JPEGs are ignored; a stereo pair
    yields its cam0/preview/left member.
    """
    if not isinstance(image, dict) or image.get('dropped'):
        return None
    kind = image.get('kind')
    if kind == 'jpg':
        return None if image.get('is_reference') else image
    if kind == 'raw':
        return image
    if kind not in ('stereo_raw', 'stereo_jpg'):
        return None
    members = [m for m in (image.get('left'), image.get('right')) if isinstance(m, dict)]
    for member in members:
        channel = str(member.get('channel_alias') or member.get('channel') or '').strip().lower()
        if channel in ('cam0', 'preview', 'left'):
            return member
    return members[0] if members else None


def open_image(image: dict[str, Any]) -> Image.Image:
    """A PIL image for a jpg or raw (GRAY8/RGB24/BGR24) SDK image.

    JPEGs are opened lazily, so their size is known before any decoding.
    """
    kind = image.get('kind')
    data = bytes(image.get('data') or b'')
    if kind == 'jpg':
        if not data:
            raise ValueError('empty JPEG image')
        return Image.open(BytesIO(data))
    if kind != 'raw':
        raise ValueError(f'unsupported image kind {kind!r}')
    width, height, fmt = int(image['width']), int(image['height']), image.get('format')
    if fmt == RAW_GRAY8:
        return Image.frombytes('L', (width, height), data)
    if fmt in (RAW_RGB24, RAW_BGR24):
        rgb = Image.frombytes('RGB', (width, height), data)
        if fmt == RAW_BGR24:
            blue, green, red = rgb.split()
            rgb = Image.merge('RGB', (red, green, blue))
        return rgb
    raise ValueError(f'unsupported raw image format {fmt!r}')


class MightyCamera:
    """Image camera part: publishes the Mighty's primary image as cam/image_array.

    The SDK callback only keeps the newest frame; decoding happens in this
    part's own thread (or in run()), so it never delays pose packets that
    share the connection. Frames are scaled down without changing their aspect
    ratio: a size the camera cannot return raises CameraError naming the
    myconfig.py change that fixes it. image_w/image_h of None mean the full
    frame. Output is uint8 RGB (H, W, 3) for image_d=3, or (H, W) for 1.

    The camera sets its own frame rate. With a framerate (CAMERA_FRAMERATE),
    startup measures the received rate for fps_check_secs and fails if the
    camera cannot keep up; images are then published at most that often, and
    a rate that later falls short (VIO starting, say) logs one warning.
    """
    RATE_WINDOW_SECS: ClassVar[float] = 5.0
    DUE_FRACTION: ClassVar[float] = 0.9  # of a period; absorbs camera jitter

    def __init__(self, url: str = 'http://192.168.7.1',
                 image_w: Optional[int] = 160, image_h: Optional[int] = 120,
                 image_d: int = 3, warmup_secs: float = 5.0,
                 stale_secs: float = 1.0, framerate: Optional[float] = None,
                 fps_check_secs: float = 2.0) -> None:
        if image_d not in (1, 3):
            raise ValueError('MightyCamera image_d must be 1 (mono) or 3 (RGB)')
        if not all(math.isfinite(v) and v > 0 for v in (warmup_secs, stale_secs, fps_check_secs)):
            raise ValueError('MightyCamera warmup_secs, stale_secs and fps_check_secs '
                             'must be finite and positive')
        if framerate is not None and not (math.isfinite(framerate) and framerate > 0):
            raise ValueError('MightyCamera framerate (CAMERA_FRAMERATE) must be finite and positive')
        self.url = url
        self.image_d = image_d
        self.stale_secs = stale_secs
        self.framerate = framerate
        self.measured_fps: Optional[float] = None
        self.last_published: Optional[float] = None
        self.rate_window: Optional[tuple[float, int]] = None
        self.warned_rate = False
        self.lock = threading.Lock()
        self.new_frame = threading.Event()
        self.pending: Optional[dict[str, Any]] = None
        self.received_at: Optional[float] = None
        self.frames_received = 0
        self.frame: Optional[np.ndarray] = None
        self.running = True
        self.released = False
        self.warned_stale = False
        self.warned_size = False
        self.warned_decode = False
        self.link = MightyLink.acquire(url)
        self.client = self.link.client
        self.unsubscribers: list[Callable[[], None]] = [self.client.on_image(self.on_image)]
        try:
            self.link.connect()
            if not self.new_frame.wait(warmup_secs):
                raise CameraError(
                    f'MightyCamera received no image from {url} within {warmup_secs:g} s. '
                    f'Check the USB cable and that {url} opens in a browser on this machine.')
            with self.lock:
                first = self.pending
            assert first is not None
            self.native: Size = open_image(first).size
            self.size: Size = (image_w if image_w is not None else self.native[0],
                               image_h if image_h is not None else self.native[1])
            error = image_size_error(self.size[0], self.size[1], self.native)
            if error:
                raise CameraError(error)
            if not self.poll():
                raise CameraError(f'MightyCamera could not decode its first image from {url}')
            if framerate is not None:
                self.measured_fps = self.measure_fps(fps_check_secs)
                error = framerate_error(framerate, self.measured_fps)
                if error:
                    raise CameraError(error)
        except BaseException:
            self.release()
            raise
        logger.info('MightyCamera ready: %dx%d depth %d from %dx%d frames%s',
                    self.size[0], self.size[1], image_d, *self.native,
                    '' if framerate is None else
                    f'; camera at {self.measured_fps:.1f} fps, publishing up to {framerate:g} fps')

    def measure_fps(self, seconds: float) -> float:
        """Frames per second received over the next `seconds`."""
        with self.lock:
            count, started = self.frames_received, time.monotonic()
        time.sleep(seconds)
        with self.lock:
            count, ended = self.frames_received - count, time.monotonic()
        return count / (ended - started) if ended > started else 0.0

    def seconds_until_due(self, now: float) -> float:
        """How long until the next image may be published under framerate."""
        if self.framerate is None or self.last_published is None:
            return 0.0
        return self.last_published + self.DUE_FRACTION / self.framerate - now

    def check_rate(self, now: float) -> None:
        """Every RATE_WINDOW_SECS, warn once if the camera falls below framerate."""
        if self.framerate is None:
            return
        with self.lock:
            received = self.frames_received
        if self.rate_window is None:
            self.rate_window = (now, received)
            return
        started, count = self.rate_window
        elapsed = now - started
        if elapsed < self.RATE_WINDOW_SECS:
            return
        self.rate_window = (now, received)
        rate = (received - count) / elapsed
        if framerate_error(self.framerate, rate):
            if not self.warned_rate:
                logger.warning('MightyCamera: the camera is now sending %.1f fps, below '
                               'CAMERA_FRAMERATE = %g; images repeat between frames. It drops '
                               'to about 15 fps while VIO runs. Set CAMERA_FRAMERATE = %d or '
                               'lower in myconfig.py.', rate, self.framerate,
                               max(1, math.floor(rate)))
                self.warned_rate = True
        elif self.warned_rate:
            logger.info('MightyCamera: frame rate back to %.1f fps', rate)
            self.warned_rate = False

    def on_image(self, image: Any) -> None:
        """SDK callback: keep only the newest primary frame; no decoding here."""
        selected = primary_image(image)
        if selected is None:
            return
        with self.lock:
            self.pending = selected
            self.received_at = time.monotonic()
            self.frames_received += 1
            self.new_frame.set()

    def poll(self) -> bool:
        """Decode the newest pending frame into self.frame; True if it updated.

        With a framerate, a frame that arrives before the next one is due
        stays pending (newer frames replace it) instead of being published.
        """
        now = time.monotonic()
        self.check_rate(now)
        if self.seconds_until_due(now) > 0:
            return False
        with self.lock:
            image, self.pending = self.pending, None
            self.new_frame.clear()
            received_at = self.received_at
        if image is None:
            if (received_at is not None and not self.warned_stale
                    and now - received_at > self.stale_secs):
                logger.warning('MightyCamera: no new image for over %g s; repeating the last one',
                               self.stale_secs)
                self.warned_stale = True
            return False
        if self.warned_stale:
            logger.info('MightyCamera: images resumed')
            self.warned_stale = False
        try:
            picture = open_image(image)
            if picture.size != self.native:
                if not self.warned_size:
                    logger.error('MightyCamera: frames changed from %dx%d to %dx%d; dropping them '
                                 'rather than stretching. Restart to use the new size.',
                                 *self.native, *picture.size)
                    self.warned_size = True
                return False
            picture = picture.convert('L' if self.image_d == 1 else 'RGB')
            if picture.size != self.size:
                picture = picture.resize(self.size, Image.Resampling.BOX)
            self.frame = np.asarray(picture, dtype=np.uint8)
            self.last_published = now
            return True
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if not self.warned_decode:
                logger.error('MightyCamera: cannot decode image: %s', exc)
                self.warned_decode = True
            return False

    def update(self) -> None:
        while self.running:
            self.new_frame.wait(0.1)
            wait = self.seconds_until_due(time.monotonic())
            if wait > 0:
                time.sleep(min(wait, 0.1))
                continue
            self.poll()

    def run_threaded(self) -> Optional[np.ndarray]:
        return self.frame

    def run(self) -> Optional[np.ndarray]:
        self.poll()
        return self.frame

    def release(self) -> None:
        """Unsubscribe and give up this part's share of the link, once."""
        with self.lock:
            if self.released:
                return
            self.released = True
        for unsubscribe in self.unsubscribers:
            if callable(unsubscribe):
                unsubscribe()
        self.link.release()

    def shutdown(self) -> None:
        self.running = False
        self.release()


def snapshot(args: argparse.Namespace) -> int:
    try:
        camera = MightyCamera(url=args.url, image_w=args.width, image_h=args.height,
                              image_d=args.depth, warmup_secs=args.warmup,
                              framerate=args.framerate, fps_check_secs=args.fps_check)
    except CameraError as exc:
        print(exc, file=sys.stderr)
        return 1
    try:
        start, started = camera.frames_received, time.monotonic()
        thread = threading.Thread(target=camera.update, daemon=True)
        thread.start()
        time.sleep(args.seconds)
        elapsed = time.monotonic() - started
        fps = (camera.frames_received - start) / elapsed
        camera.running = False
        thread.join(1.0)
        assert camera.frame is not None
        Image.fromarray(camera.frame).save(args.out)
        print(f'Camera frames {camera.native[0]}x{camera.native[1]} '
              f'({aspect_name(*camera.native)}); saved {camera.size[0]}x{camera.size[1]} '
              f'depth {camera.image_d} to {args.out}; '
              f'{fps:.1f} fps received over {elapsed:.1f} s')
        return 0
    finally:
        camera.shutdown()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m donkeycar.parts.mighty',
                                     description='MightyCamera hardware checks.')
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot', help='save one frame and report the received frame rate')
    snap.add_argument('--url', default='http://192.168.7.1')
    snap.add_argument('--out', default='mighty-snapshot.jpg')
    snap.add_argument('--seconds', type=float, default=5.0, help='how long to count frames')
    snap.add_argument('--width', type=int, default=None, help='IMAGE_W to test (default: full frame)')
    snap.add_argument('--height', type=int, default=None, help='IMAGE_H to test (default: full frame)')
    snap.add_argument('--depth', type=int, choices=(1, 3), default=3)
    snap.add_argument('--warmup', type=float, default=5.0)
    snap.add_argument('--framerate', type=float, default=None,
                      help='CAMERA_FRAMERATE to test (default: no frame-rate check)')
    snap.add_argument('--fps-check', type=float, default=2.0,
                      help='seconds to measure the rate for the --framerate check')
    args = parser.parse_args(argv)
    return snapshot(args)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
