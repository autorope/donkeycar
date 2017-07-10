Physical Interfaces
-------------------

- Holes in Raspberry Pi are M2.5 placed at 49x58 mm.
- Holes in PCA9685 are M2.5 placed 20x56 mm.
- Holes in plate for front of car are M5. 28 mm apart.
- Holes in plate for back of car are M5. 33 mm apart.
- Rollbar front holes are M2.5 placed 86 mm apart.
- Rollbar back hole is M2.5 at a distance of 159 mm from front holes.

Config
------

From `~/mydonkey/vehicle.ini` on Raspberry Pi.

```
[vehicle]
id=mycar
loop_delay=.08

[camera]
loop_delay = .08

[throttle_actuator]
channel=0
max_pulse=300
zero_pulse=370
min_pulse=340

[steering_actuator]
channel=1
left_pulse=450
right_pulse=300

[pilot]
model_path=~/mydonkey/models/default.h5
```
