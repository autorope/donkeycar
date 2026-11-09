# MightyCamera native pose for path following

MightyCamera supplies local position and orientation directly to the
`path_follow` template, using the same pose abstraction as the T265 and
odometry. The integration consists of two independent parts:

- `MightyPose` subscribes to the SDK's public body-pose stream and outputs
  `mighty/pose` (the raw SDK dictionary), `mighty/fresh`, and `mighty/timing`.
  It handles connection state, tracking resets, freshness and timestamp ordering.
- `MightyPoseTransform` validates and converts the raw pose to `pos/x`, `pos/y`
  in local metres, `pos/angle` in radians counterclockwise from positive X, and
  `mighty/valid`. It applies configurable map yaw and body-forward orientation.

There are no synthetic geographic coordinates, UTM projections or NMEA
sentences in the Mighty pipeline. The standard origin-reset part translates
local XY to the recorded route's origin after the transform.

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
HAVE_GPS = False  # set True only when also using an actual serial GPS
CAMERA_TYPE = 'MOCK'  # optional when using only the path map in the UI
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

Local trials also patched the separately installed SDK HTTP reader in
`mighty_sdk/web_device.py`: `resp.read(self.read_chunk_size)` became
`resp.read1(self.read_chunk_size)` to return available bytes instead of waiting
for a full 64 KiB block. This external change is not installed by Donkeycar;
check your SDK version when reproducing the trials.

Hardware-free tests cover native coordinates and heading, stream freshness,
invalid data, timestamp ordering and reset, validity gates, look-ahead driving,
and template construction with Mighty alone, GPS alone, and both sources
(including GPS/IMU fusion). Hardware helpers are mocked; no driving is started.
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
