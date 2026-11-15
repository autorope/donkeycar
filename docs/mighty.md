# MightyCamera: native pose and image camera

MightyCamera supplies local position and orientation directly to the
`path_follow` template, using the same pose abstraction as the T265 and
odometry. It can also be the car's image camera (`CAMERA_TYPE = "MIGHTY"`); see
[Image camera](#image-camera-camera_type--mighty). The pose integration consists
of two independent parts:

- `MightyPose` subscribes to the SDK's public body-pose stream and outputs
  `mighty/pose` (the raw SDK dictionary), `mighty/fresh`, and `mighty/timing`.
  It handles connection state, tracking resets, freshness and timestamp ordering.
- `MightyPoseTransform` validates and converts the raw pose to `pos/x`, `pos/y`
  in local metres, `pos/angle` in radians counterclockwise from positive X, and
  `mighty/valid`. It applies configurable map yaw and body-forward orientation.

There are no synthetic geographic coordinates, UTM projections or NMEA
sentences in the Mighty pipeline. The standard origin-reset part translates
local XY to the recorded route's origin after the transform.

Every Mighty part for one URL shares a single SDK connection (`MightyLink`):
the first part to connect opens the stream and the last to shut down closes
it. The stream is read `MIGHTY_READ_CHUNK_BYTES` (default 1024) at a time.

## Setup

Install the optional SDK in your Donkeycar environment and create a car:

```sh
python -m pip install 'git+https://github.com/asadm/mighty-protocol.git'
donkey createcar --path ~/mycar --template path_follow
```

Retain your car's drivetrain/controller settings and add these overrides:

```python
HAVE_MIGHTY = True
MIGHTY_URL = 'http://192.168.7.1'
MIGHTY_START_VIO = True
MIGHTY_MAX_AGE = 0.5
MIGHTY_YAW_DEGREES = 0.0
MIGHTY_HEADING_OFFSET_DEGREES = 0.0
MIGHTY_HIGH_RATE_POSE = False
MIGHTY_LOG_DIRECTORY = 'logs'
MIGHTY_READ_CHUNK_BYTES = 1024
HAVE_GPS = False  # set True only when also using an actual serial GPS
CAMERA_TYPE = 'MOCK'  # or 'MIGHTY' to use the Mighty's own images; see below
AUTO_RECORD_ON_THROTTLE = False
```

Connect the camera over USB Ethernet and run `python manage.py drive`.
If the camera rejects the VIO start request, start VIO in its visualizer.
`Mighty pose stream: fresh` confirms receipt of current tracking data;
`DriveTelemetry ... valid=True` additionally confirms valid position,
confidence and orientation after conversion.

At the physical starting point, reset origin and record the route manually.
Stop recording and save using the configured path buttons. Return to the same
physical position and heading before replay. Saved paths load on startup.
VIO restart, drift or loop closure can change the map. This integration does
not provide map persistence or automatically recover alignment.

`MIGHTY_YAW_DEGREES` rotates both local XY and heading counterclockwise.
`MIGHTY_HEADING_OFFSET_DEGREES` identifies vehicle forward in camera body XY:
0 means +X, 90 means +Y. The transform normalizes the body quaternion and
projects this forward axis onto the ground plane. Invalid or near-vertical
forward projections cannot supply a driving pose.

## Image camera (`CAMERA_TYPE = "MIGHTY"`)

`MightyCamera` publishes the Mighty's primary (`cam0`) image as
`cam/image_array`, like `PICAM`, `WEBCAM` or `CVCAM`. It is available in the
`complete` and `path_follow` templates. With `HAVE_MIGHTY = True` as well, the
pose reader and the camera share one connection.

| Template | `CAMERA_TYPE = "MIGHTY"` |
| --- | --- |
| `complete` | Supported. |
| `path_follow` | Supported, alone or with `HAVE_MIGHTY`. |
| `cv_control` | Refused at startup. Its `LineFollower` finds the line by colour, and the Mighty is monochrome. A custom `CV_CONTROLLER_MODULE`/`CV_CONTROLLER_CLASS` that works on greyscale is allowed. |
| `basic` | Not supported ("Unkown camera type"). |

### What the camera gives

The camera decides its own image size, colour and frame rate; donkeycar cannot
change them. Measured with firmware `Mighty v.2026-10-01-e2aac61`:

- **Size:** 640×400 (16:10) JPEG frames.
- **Colour:** monochrome. The JPEGs carry three identical channels.
- **Frame rate:** about 18 fps with VIO off, typically 12–16 fps while VIO
  runs, and drifting over a long session. In a `path_follow` drive that
  started VIO and streamed the web UI at 640×400, it fell as low as 8.7 fps
  for a while, after a pause of over 1 s.

`MightyCamera` scales frames down without changing their shape, and it never
invents colour or frames. At startup it checks the configuration against the
first frame and a 2 s rate measurement. It reports **every** problem in one
error, so a single restart fixes them all.

| Setting | Rule | If it fails |
| --- | --- | --- |
| `IMAGE_W`, `IMAGE_H` | Exactly 16:10 and no larger than 640×400. Valid sizes are 8k×5k, e.g. 80×50, 160×100, 192×120, 320×200, 640×400. | The error suggests the valid size with the most pixels that keeps your width or your height, plus the full frame. |
| `IMAGE_DEPTH` | 1. Output is a 2-D (H, W) `uint8` array. | "set IMAGE_DEPTH = 1" |
| `CAMERA_FRAMERATE` | At most 5% above the rate measured at startup (from the camera's capture timestamps). | The error names the largest whole rate that passes. Leave a few fps of margin, because the rate drops once VIO runs. |

Every template's defaults fail all three: for example 160×120, depth 3 and
20 fps. The error then reads (rates vary from run to run):

```text
MightyCamera cannot start: 3 settings in myconfig.py need changing.
  1. MightyCamera cannot return IMAGE_W=160, IMAGE_H=120 without stretching: the camera sends 640x400 (16:10). In myconfig.py set IMAGE_W = 192 and IMAGE_H = 120 (keeps your height), or IMAGE_W = 640 and IMAGE_H = 400 (the full frame). Any 16:10 size up to 640x400 works.
  2. MightyCamera cannot return IMAGE_DEPTH = 3: the camera is monochrome, so there is no colour to return. In myconfig.py set IMAGE_DEPTH = 1.
  3. MightyCamera cannot deliver CAMERA_FRAMERATE = 20: the camera is sending 14.3 fps. The camera sets its own rate, and it drops to about 15 fps while VIO runs. In myconfig.py set CAMERA_FRAMERATE = 15, or anything lower.
```

While driving, the camera publishes at most `CAMERA_FRAMERATE` images per
second. A frame that arrives slightly early waits rather than being dropped.
Two conditions log a warning and keep running rather than stopping the car:

- the camera's rate falls below `CAMERA_FRAMERATE` over a 5 s window, as it
  does when `path_follow` starts VIO after the check;
- no new image arrives for 1 s, in which case the last image repeats.

A mid-run change in frame size drops those frames and logs one error.

### Configuration

Add these to the car's `myconfig.py`. The values below are an example that
passes on the camera described above:

```python
CAMERA_TYPE = "MIGHTY"
IMAGE_W = 160                        # 16:10: 160x100, 320x200, 640x400, ...
IMAGE_H = 100
IMAGE_DEPTH = 1                      # the camera is monochrome
CAMERA_FRAMERATE = 12                # below the camera's rate, with margin
MIGHTY_URL = 'http://192.168.7.1'    # shared with HAVE_MIGHTY
MIGHTY_CAMERA_WARMUP_SECS = 5.0      # fail at startup if no image arrives by then
MIGHTY_CAMERA_FPS_CHECK_SECS = 2.0   # how long startup measures the frame rate
MIGHTY_READ_CHUNK_BYTES = 1024       # SDK stream read size
```

All the `MIGHTY_*` settings default to the values shown when absent, so a car
directory created from an older template still works. Without
`CAMERA_FRAMERATE` there is no frame-rate check.

### Why the stream is read in small chunks

The SDK's `MightyWebDevice` reads its HTTP stream 64 KiB at a time by default.
At about 19 KB per frame, frames reached the Pi three at a time, about every
200 ms, and poses bunched up with them. Because `MightyCamera` keeps only the
newest frame, it published about 5 distinct images per second from a 15 fps
camera. Reading 1024 bytes at a time delivers each frame and pose as it
arrives: about 15 images per second, and gaps between poses of at most about
81 ms instead of 238 ms. It made no measurable difference to CPU use. (The
SDK's reader thread uses most of a Pi core either way.)

### Hardware check (runbook)

Run these on the car (the Raspberry Pi), not the Mac. Every command is
standalone; the expected output below was recorded on murmurpi64 on
2026-11-15. Frame rates vary from run to run.

**Prerequisites**

- The Mighty is plugged into the Pi over USB and powered. It serves
  `http://192.168.7.1` over USB Ethernet.
- The donkeycar checkout on the Pi is on a branch that has this camera:
  `mighty-camera-image`, or `zlite/mighty-camera-gps` once that is merged.
- The donkeycar Python environment has the Mighty SDK (`mighty-protocol`)
  installed; see [Setup](#setup).
- Nothing else is using the camera's stream, such as a running
  `manage.py drive`.

**1. Open a shell with the environment.** On the Mac:

```sh
ssh ed@murmurpi64.local                 # your Pi's user and hostname
source ~/env/bin/activate               # your donkeycar environment
cd /tmp
```

**2. Check the SDK and the camera are reachable.**

```sh
python -c "import mighty_sdk; print(mighty_sdk.__file__)"
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.7.1/
```

Expected: a path ending in `site-packages/mighty_sdk/__init__.py`, then
`200`.

**3. Save a full frame.**

```sh
python -m donkeycar.parts.mighty snapshot --out /tmp/mighty-full.jpg
```

Expected (one line; rates vary):

```text
Camera frames 640x400 (16:10); saved 640x400 depth 1 to /tmp/mighty-full.jpg; 12.8 fps received, 13.0 distinct images published per second over 5.0 s
```

Copy `/tmp/mighty-full.jpg` to the Mac (`scp ed@murmurpi64.local:/tmp/mighty-full.jpg .`)
to view it: a grey wide-angle image. "distinct images published" should be
close to "fps received". If it is about a third of it, the stream is being
read in 64 KiB blocks: check `MIGHTY_READ_CHUNK_BYTES`.

**4. Check the startup error with a template's default settings.**

```sh
python -m donkeycar.parts.mighty snapshot --width 160 --height 120 --depth 3 --framerate 20 --out /tmp/never.jpg
echo "exit status: $?"
```

Expected: the three-part error shown in
[What the camera gives](#what-the-camera-gives), then `exit status: 1`.
No `/tmp/never.jpg` is written.

**5. Check settings that pass.**

```sh
python -m donkeycar.parts.mighty snapshot --width 160 --height 100 --framerate 12 --out /tmp/mighty-160x100.jpg
```

Expected (rates vary):

```text
INFO:__main__:MightyCamera ready: 160x100 depth 1 from 640x400 monochrome frames; camera at 13.9 fps, publishing up to 12 fps
Camera frames 640x400 (16:10); saved 160x100 depth 1 to /tmp/mighty-160x100.jpg; 13.5 fps received, 12.3 distinct images published per second over 5.0 s
```

If the frame-rate check fails here, the camera is running slower than 12 fps.
Use the rate the error suggests.

**6. Drive with the camera.** In a `complete` or `path_follow` car
directory, add the settings from [Configuration](#configuration) to
`myconfig.py`. Use the rate from step 5 if it differs. Then run:

```sh
cd ~/mycar_mighty_path_follow           # your complete or path_follow car directory
python manage.py drive
```

Expected in the log: `MightyCamera ready: ... monochrome frames; camera at
... fps, publishing up to 12 fps`. With `HAVE_MIGHTY`, starting VIO can also
log warnings while the drive keeps running. In the recorded run, these were
`MightyCamera: no new image for over 1 s; repeating the last one`,
`MightyCamera: images resumed`, and `MightyCamera: the camera is now sending
10.5 fps, below CAMERA_FRAMERATE = 12; ...`. Lower `CAMERA_FRAMERATE` if the
rate warnings persist. Open `http://murmurpi64.local:8887` (your
Pi's hostname) on the Mac: the web UI shows the live grey image. With
`HAVE_MIGHTY = True` too, `ss -tn | grep -c 192.168.7.1:80`, run in a second
shell on the Pi, prints `1`, meaning one connection shared by poses and
images. Stop the drive with Ctrl-C.

**7. Clean up.**

```sh
rm -f /tmp/mighty-full.jpg /tmp/mighty-160x100.jpg
```

## GPS coexistence

`HAVE_MIGHTY` is independent of `HAVE_GPS`. When both are enabled, Mighty
supplies the driving pose. Serial GPS measurements remain available on
`gps/nmea`, `gps/positions`, and `gps/utm/*`; optional GPS/IMU fusion publishes
`gps/fused/x`, `gps/fused/y`, and `gps/fused/yaw` instead of overwriting the
Mighty pose. GPS playback is disabled while Mighty is selected. With Mighty
disabled, the existing serial GPS pose and playback behavior is retained.

There is no automatic GPS fallback or GPS/Mighty fusion: their local and
geographic frames require explicit alignment before combining them. A Mighty
tracking failure stops autonomous output even if serial GPS is available.

## Validity and ordering

Disconnected, stale, non-tracking, low-confidence or malformed poses invalidate
`mighty/valid`. Missing/invalid orientation also invalidates the complete pose.
Waypoint recording is inhibited and autonomous steering/throttle are zeroed
in both full-auto and assisted-steering modes. Manual control passes through.

Only public body poses with strictly increasing positive camera timestamps are
accepted. Older, duplicate and timestamp-less packets cannot replace a pose or
refresh its age. Explicit camera resets and VIO off/initializing transitions
start a new timestamp epoch; ordinary tracking loss does not. Returning to
tracking requires another fresh pose.

## Optional finite-route controller

The defaults use the existing closed-route PID controller. To use the
experimental finite-route look-ahead controller, set:

```python
PATH_CLOSED = False
PATH_USE_LOOKAHEAD = True
PATH_LOOKAHEAD_METERS = 1.5
PATH_WHEELBASE_METERS = 0.25
PATH_MAX_STEERING_DEGREES = 30.0
PATH_STEERING_SIGN = -1.0
PATH_STEERING_GAIN = 0.75
PATH_MAX_ERROR_METERS = 0.75
PATH_CORNER_MIN_THROTTLE_FACTOR = 0.7
PATH_FINISH_RADIUS = 0.25
MIGHTY_HIGH_RATE_POSE = True
```

Measure wheelbase and full steering angle for your car and verify steering
sign. Route progress search is bounded and forward-only. Excess path error or
a target behind the car latches a stop; select manual mode to rearm. The
endpoint guard stops within the finish radius. Corner preview reduces throttle
toward `PATH_CORNER_MIN_THROTTLE_FACTOR` times base speed. Look-ahead uses
`PID_THROTTLE` as its base speed, subsequently scaled by `AI_THROTTLE_MULT`.

## Timing diagnostics and validation

The firmware-dependent high-rate option requests predicted pose output.
Bounded asynchronous `mighty-timing-*.jsonl` logs include raw and rejected
packets, camera timestamps, Pi arrivals, relative extra delay, reader samples,
and SDK statistics. Reader sample `valid` denotes freshness; console
`DriveTelemetry` records transformed-pose validity and steering, with
`DrivePoseTiming` identifying the consumed pose. Camera and Pi clocks do not
establish absolute camera latency. Translation-health reports are logged
without an additional observability-based stop policy.

Earlier local trials patched the separately installed SDK HTTP reader in
`mighty_sdk/web_device.py`: `resp.read(self.read_chunk_size)` became
`resp.read1(self.read_chunk_size)`, to return available bytes instead of
waiting for a full 64 KiB block. That patch is no longer needed: `MightyLink`
creates the device with `read_chunk_size = MIGHTY_READ_CHUNK_BYTES` (default
1024), which has the same effect on an unpatched SDK. See
[Why the stream is read in small chunks](#why-the-stream-is-read-in-small-chunks).

Hardware-free tests cover native coordinates and heading, stream freshness,
invalid data, timestamp ordering and reset, validity gates, look-ahead driving,
and template construction with Mighty alone, GPS alone, and both sources
(including GPS/IMU fusion). Hardware helpers are mocked; no driving is started.
Further tests cover the image camera: the shared connection, the size, depth
and frame-rate rules and their messages, frame selection and pacing, the
`snapshot` CLI, the `complete`, `path_follow` and `cv_control` templates, and
the read chunk size (`test_mighty.py`, `test_mighty_camera.py`,
`test_mighty_templates.py`, `test_path_follow_mighty.py`).
The direct-pose implementation still requires live validation. Earlier local
trials of the controller and ordering fixes improved tracking but showed
occasional departures and origin/heading alignment problems.

## Migration from the draft GPS bridge

Update the template and configuration together. Remove `GPS_SOURCE='mighty'`;
startup rejects that obsolete selector before constructing hardware. Enable
`HAVE_MIGHTY` and rename the settings:

| Old setting | New setting |
| --- | --- |
| `MIGHTY_GPS_URL` | `MIGHTY_URL` |
| `MIGHTY_GPS_START_VIO` | `MIGHTY_START_VIO` |
| `MIGHTY_GPS_MAX_AGE` | `MIGHTY_MAX_AGE` |
| `MIGHTY_GPS_YAW` | `MIGHTY_YAW_DEGREES` |

Remove `MIGHTY_GPS_LAT` and `MIGHTY_GPS_LON`; no geographic anchor is needed.
Set `HAVE_GPS=False` unless a real serial GPS is connected. Heading-offset and
high-rate settings retain their names. The raw reader and transform live in
`donkeycar.parts.mighty`; the old `mighty_gps` module has been removed.
