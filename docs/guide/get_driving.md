# Drive your car.

After you've calibrated your car you can start driving it.

### Start your car.

> *** Put your car in a safe place where the wheels are off the ground ***
This is the step were the car can take off.

---
# Normal usage
In future runs, when you start a new session, you will want to:

On Windows:

* start a new Anaconda Prompt from Windows start menu
* Activate mappings to donkey Python setup with: ```activate donkey```
* Change to your local dir for managing donkey: ```cd ~/mycar```
* Find your pi



This will show your IP address, prompt for your password, and then search
for your cars IP address.

> If your car's IP address is not shown:
>
> 1. Find another way to scan your local network for your raspberry pi
> 2. Connect a monitor/keyboard and ensure your pi is connected to the the same wifi network as your computer.


Assuming that you did find your pi on the network, you can now connect to it via SSH.

```
ssh pi@<your_pi_ip_address>
```

The default user name is 'pi' and the password is 'raspberry'.  If you are using the pre-built Donkey image, the password is 'asdfasdf'.


### Make sure you've created your car application.
```
donkey createcar ~/mycar --template donkey2
```

See also [more information.](/utility/donkey/#create-car)

#### Start your car.
Open your car's folder and start your car.
```
cd ~/mycar
python manage.py drive
```

This script will start the drive loop in your car which includes a part that
is a web server for you to control your car. You can now control your car
from a web browser at the URL: `<your car's IP's address>:8887`

![drive UI](../assets/drive_UI.png)

## Driving with Web Controller
On your phone you can now press start to set your phones current tilt to be
zero throttle and steering. Now tilting your phone forward will increase throttle and tilting it side to side will turn the steering.


### Features
* Recording - Press record data to start recording images, steering angels and throttle values.
* Throttle mode - Option to set the throttle as constant. This is used in
races if you have a pilot that will steer but doesn't control throttle.
* Pilot mode - Choose this if the pilot should control the angle and/or throttle.
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

Check the [Controllers](/parts/controllers/#physical-joystick-controller) section to read about setting up the bluetooth connection.






