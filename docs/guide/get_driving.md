# Drive your car.

After you've calibrated your car you can start driving it. 

### Start your car.
 
> *** Put your car in a safe place where the wheels are off the ground *** This
is the step were the car can take off. 

Open your car's folder and start our car. 
```
cd ~/d2
python manage.py drive
```

This script will start the drive loop in your car which includes a part that 
is a webserver for you to control your car. You can now controll your car
from a web browser at the url: `<your car's ip's address>:8887`

![drive UI](../assets/drive_UI.png)

## Driving
On your phone you can now press start to set your phones current tilt to be
zero throttle and steering. Now tilting your phone forward will increase throttle
and tilting it side to side will turn the steering. 


### Features
* Recording - Press record data to start recording images, steering angels and throttle values. 
* Throttle mode - Option to set the throttle as constant. This is used in 
races if you have a pilot that will steer but doesn't control throttle. 
* Pilot mode - Choose if the pilot should control the angle and/or throttle.
* Max throttle - Select the maximum throttle.

### Keyboard shortcuts
* `space` : stop car and stop recording
* `r` : toggle recording
* `i` : increase throttle
* `k` : decrease throttle
* `j` : turn left 
* `l` : turn right 

