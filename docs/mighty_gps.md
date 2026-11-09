# MightyCamera indoor path following

MightyCamera body poses can supply indoor positioning to the `path_follow`
template through the existing NMEA-to-UTM GPS pipeline. This uses VIO poses,
not camera images or measured geographic GPS coordinates.

Install the optional SDK in your Donkeycar environment:

```sh
python -m pip install 'git+https://github.com/asadm/mighty-protocol.git'
donkey createcar --path ~/mycar --template path_follow
```

Set these overrides in `myconfig.py`, retaining your drivetrain and controller
configuration:

```python
HAVE_GPS = True
GPS_SOURCE = 'mighty'
MIGHTY_GPS_URL = 'http://192.168.7.1'
MIGHTY_GPS_START_VIO = True
MIGHTY_GPS_LAT = 37.0
MIGHTY_GPS_LON = -122.0
MIGHTY_GPS_YAW = 0.0
MIGHTY_GPS_MAX_AGE = 0.5
GPS_NMEA_PATH = None
CAMERA_TYPE = 'MOCK'  # optional when using only the path map in the UI
AUTO_RECORD_ON_THROTTLE = False
```

Connect the camera over USB Ethernet and run `python manage.py drive`.
No standalone bridge or virtual serial port is required. If the camera does
not accept the VIO start request, start VIO in its visualizer.

Wait for `Mighty GPS fix: valid`, then reset the origin at your physical start
position, toggle recording, and drive the route manually. Stop recording and
save the path using the configured path buttons. Return to the same physical
start and reset the origin before replaying in autopilot mode. Saved paths
load automatically at startup.

The synthetic latitude/longitude anchor selects a UTM projection; inverse
projection preserves local meter offsets through Donkeycar's GPS parser.
Yaw rotates local XY into UTM east/north in degrees counterclockwise.
Disconnected, stale, low-confidence, non-body, or non-tracking poses produce
invalid fixes. Waypoint recording is inhibited and autonomous steering and
throttle are zeroed while fixes are invalid. Manual control remains available.
Recorded NMEA playback is disabled for this source even if `GPS_NMEA_PATH`
is set, so live validity and autonomous position refer to the same source.

VIO drift, resets, and loop closure can change coordinates. After restarting
VIO, match the map heading as well as the origin. This integration does not
persist the VIO map. Local driving trials show improved tracking after rejecting
late poses, but repeatable autonomous completion remains unverified.


## Experimental finite-route controller and diagnostics

The template keeps the existing closed-route PID defaults. To try the finite
route controller used in local trials, set:

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
MIGHTY_HEADING_OFFSET_DEGREES = 0.0
MIGHTY_HIGH_RATE_POSE = True
```

Measure wheelbase and full steering angle for your car, and verify steering
sign and body-forward axis. Heading is projected from the body quaternion;
Mighty look-ahead driving stops when orientation is unavailable. Route progress
search is bounded and forward-only. Excess path error or a target behind the
car latches a stop, including assisted steering mode; manual mode rearms it.
The endpoint guard stops within the finish radius. Corner preview reduces
throttle by up to the configured factor. Look-ahead uses PID_THROTTLE as its
base speed, scaled subsequently by AI_THROTTLE_MULT.

The firmware-dependent high-rate option requests predicted pose output.
Only public body poses with strictly increasing positive camera timestamps
are accepted. Late, duplicate and timestamp-less packets do not replace the
current pose or refresh its age. Explicit resets and VIO off/initializing
transitions start a new timestamp epoch; ordinary tracking loss does not.

Mighty readers write bounded asynchronous `logs/mighty-timing-*.jsonl` files,
including rejected packets, camera timestamps, Pi arrival times, relative extra
delay, control-cycle samples, and SDK statistics. Console DriveTelemetry and
DrivePoseTiming records correlate steering with the pose used. These clocks do
not establish absolute camera latency. Translation-health reports are logged;
no additional translation-observability stop threshold has been implemented.

Local trials also patched the separately installed Mighty SDK HTTP reader in
`mighty_sdk/web_device.py`: replace `resp.read(self.read_chunk_size)` with
`resp.read1(self.read_chunk_size)` to return available bytes instead of waiting
for a full 64 KiB block. This external dependency change is not installed by
this Donkeycar PR; check your SDK version before reproducing the trials.

Hardware-free regression tests cover pose conversion, heading, ordering,
resets, look-ahead steering, stop/rearm behavior, and simulated path recovery.
The local Python 3.11 / Donkeycar 5.2 run passed 27 tests. Full upstream CI and
repeatable live route completion remain outstanding. Trials still showed
occasional large departures and origin/heading alignment errors.
