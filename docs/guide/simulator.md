# Donkey Simulator

The [Donkey Gym](https://github.com/tawnkramer/gym-donkeycar) project is a OpenAI gym wrapper around the [Self Driving Sandbox](https://github.com/tawnkramer/sdsandbox/tree/donkey) donkey simulator. When building the sim from source, checkout the `donkey` branch of the sdsandbox project. 


The simulator is built on the the Unity game platform, uses their internal physics and graphics, and connects to a donkey Python process to use our trained model to control the simulated Donkey.

## My Virtual Donkey

There are many ways to use the simulator, depending on your goals. You can use the simulator to get to know and use the standard Donkeycar drive/train/test cycle by treating it as virtual hardware. You will collect data, drive, and train using the __same commands__ as if you were using a real robot. We will walk through that use-case first.

![sim_screen_shot](../assets/sim_screen_shot.png)

### Install

* Download and unzip the simulator for your host pc platform from [Donkey Gym Release](https://github.com/tawnkramer/gym-donkeycar/releases).
* Place the simulator where you like. For this example it will be ~/projects/DonkeySimLinux. Your dir will have a different name depending on platform. 
* Complete all the steps to [install Donkey on your host pc](install_software.md#step-1-install-software-on-host-pc).
* Setup DonkeyGym: 
```
cd ~/projects
git clone https://github.com/tawnkramer/gym-donkeycar
conda activate donkey
pip install -e gym-donkeycar
```
* You may use an existing ~/mycar donkey application, or begin a new one. Here we will start fresh: 
```
donkey createcar --path ~/mysim
cd ~/mysim
```
* Edit your myconfig.py to enable donkey gym simulator wrapper:
```
DONKEY_GYM = True
DONKEY_SIM_PATH = "/home/tkramer/projects/DonkeySimLinux/donkey_sim.x86_64"
DONKEY_GYM_ENV_NAME = "donkey-generated-track-v0"
```
> Note: your path to the executable will vary depending on platform and user.

### Drive

You may use all the normal commands to manage.py at this point. Such as:
```
python manage.py drive
```
This should start the simulator and connect to it automatically. By default you will have a web interface to control the donkey. Navigate to http://localhost:8887/drive to see control page.

On Ubuntu Linux only, you may plug in your joystick of choice. If it mounts as /dev/input/js0 then there's a good chance it will work. Modify myconfig.py to indicate your joystick model and use the --js arg to run.
```
python manage.py drive --js
```

As you drive, this will create a tub of records in your data dir as usual.

### Train

You will not need to rsync your data, as it was recorded and resides locally. You can train as usual:
```
python manage.py train --model models/mypilot.h5
```

### Test

You can use the model as usual:
```
python manage.py drive --model models/mypilot.h5
```

Then navigate to web control page. Set `Mode and Pilot` to `Local Pilot(d)`. The car should start driving.

### Sample Driving Data

Here's some sample drivng data to get you started. [Download this](https://drive.google.com/open?id=1A5sTSddFsf494UDtnvYQBaEPYX87_LMp) and unpack it into your data dir. This should train to a slow but stable driver.