# Drive your car.

After you've calibrated your car you can start driving it. 

### Start your car.
 
> *** Put your car in a safe place where the wheels are off the ground *** This
is the step were the car can take off. 

---
# Normal usage
In future runs, when you start a new session, you will want to:

On Windows:

* start a new Anaconda Prompt from windows start menu
* Activate mappings to donkey python setup with: ```activate donkey```
* Change to your local dir for managing donkey: ```cd ~/d2```
* Find your pi



This will show your ip address, promt for your password, and then search 
for your cars ip address. 

> If your car's ip address is not shown then:
>
> 1. find another way to scan your local network for your raspbery pi 
> 2. connect a monitor to your pi to connect to the the same wifi as your computer. 


Assuming that you did find your pi on the network. You can now connect to it
remotely via ssh. 

```
ssh pi@<your_pi_ip_address>
```

The default username is 'pi' and the password is 'raspberry'


### Create your car application.

```
donkey createcar --template donkey2 --path ~/d2
```

#### Start your car.
Open your car's folder and start our car. 
```
cd ~/d2
python manage.py drive
```

This script will start the drive loop in your car which includes a part that 
is a webserver for you to control your car. You can now controll your car
from a web browser at the url: `<your car's ip's address>:8887`

![drive UI](../assets/drive_UI.png)

## Driving with Web Controller
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

----

## Driving with Physical Joystick Controller

You may find that it helps to use a physical joystick device to control your vehicle.

### Setup Bluetooth and pair joystick
Check the [Controllers](/parts/controllers/#physical-joystick-controller) section to read about setting up the bluetooth connection.

### Start car
```
cd ~/d2
python manage.py drive --js
```

Optionally, if you want joystick use to be sticky and don't want to add the --js each time, modify your config.py so that USE_JOYSTICK_AS_DEFAULT = True
```
nano config.py
```


### Joystick Controls

* left analog stick left and right to adjust steering
* right analog stick forward to increase forward throttle
* pull back twice on right analog to reverse

> Whenever the throttle is not zero, driving data will be recorded - as long as you are in User mode!

* select button switches modes - "User, Local Angle, Local(angle and throttle)"
* Triangle - increase max throtlle
* X  - decrease max thottle
* Circle - toggle recording(disabled by default. auto record on throttle is enabled by default)
* dpad up - increase throttle scale
* dpad down - decrease throttle scale
* dpad left - increase steering scale
* dpad right - decrease steering scale
* start - toggle constant throttle. Sets to max throttle ( modified by X and Triangle ).


### Start car for self-driving
```
cd ~/d2
python manage.py drive --model <path/to/model> --js
```

Hit Select button to toggle between three modes - User, Local Angle, and Local Throttle & Angle.

* User - User controls both steering and throttle with joystick
* Local Angle - Ai controls steering. User controls throttle.
* Local Throttle & Angle - Ai controls both steering and throttle

When the car is in Local Angle mode, the NN will steer. You must provide throttle.



