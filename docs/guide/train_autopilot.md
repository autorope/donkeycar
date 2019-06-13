
### Start car for self-driving
```
cd ~/mycar
python manage.py drive --model <path/to/model> --js
```

Hit the Select button to toggle between three modes - User, Local Angle, and Local Throttle & Angle.

* User - User controls both steering and throttle with joystick
* Local Angle - Ai controls steering, user controls throttle
* Local Throttle & Angle - Ai controls both steering and throttle

When the car is in Local Angle mode, the NN will steer. You must provide throttle.

