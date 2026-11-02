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
persist the VIO map. Live driving and hardware startup require validation.
