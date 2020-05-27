# Donkey Command-line Utilities

The `donkey` command is created when you install the donkeycar Python package. This is a Python script that adds some important functionality. The operations here are vehicle independent, and should work on any hardware configuration.

## Create Car

This command creates a new dir which will contain the files needed to run and train your robot.

Usage:

```bash
donkey createcar --path <dir> [--overwrite] [--template <donkey2>]
```

* This command may be run from any dir
* Run on the host computer or the robot
* It uses the `--path` as the destination dir to create. If `.py` files exist there, it will not overwrite them, unless the optional `--overwrite` is used.
* The optional `--template` will specify the template file to start from. For a list of templates, see the `donkeycar/templates` dir. This source template will be copied over the `manage.py` for the user.

## Find Car

This command attempts to locate your car on the local network using nmap.

Usage:

```bash
donkey findcar
```

* Run on the host computer
* Prints the host computer IP address and the car IP address if found
* Requires the nmap utility:

```bash
sudo apt install nmap
```

## Calibrate Car

This command allows you to manually enter values to interactively set the PWM values and experiment with how your robot responds.
See also [more information.](/guide/calibrate/)

Usage:

```bash
donkey calibrate --channel <0-15 channel id>
```

* Run on the host computer
* Opens the PWM channel specified by `--channel`
* Type integer values to specify PWM values and hit enter
* Hit `Ctrl + C` to exit

## Clean data in Tub

Opens a web server to delete bad data from a tub.

Usage:

```bash
donkey tubclean <folder containing tubs>
```

* Run on pi or host computer.
* Opens the web server to delete bad data.
* Hit `Ctrl + C` to exit

## Make Movie from Tub

This command allows you to create a movie file from the images in a Tub.

Usage:

```bash
donkey makemovie --tub=<tub_path> [--out=<tub_movie.mp4>] [--config=<config.py>] [--model=<model path>] [--model_type=(linear|categorical|rnn|imu|behavior|3d)] [--start=0] [--end=-1] [--scale=2] [--salient]
```

* Run on the host computer or the robot
* Uses the image records from `--tub` dir path given
* Creates a movie given by `--out`. Codec is inferred from file extension. Default: `tub_movie.mp4`
* Optional argument to specify a different `config.py` other than default: `config.py`
* Optional model argument will load the keras model and display prediction as lines on the movie
* model_type may optionally give a hint about what model type we are loading. Categorical is default.
* optional `--salient` will overlay a visualization of which pixels excited the NN the most
* optional `--start` and/or `--end` can specify a range of frame numbers to use.
* scale will cause ouput image to be scaled by this amount

## Check Tub

This command allows you to see how many records are contained in any/all tubs. It will also open each record and ensure that the data is readable and intact. If not, it will allow you to remove corrupt records.

> Note: This should be moved from manage.py to donkey command

Usage:

```bash
donkey tubcheck <tub_path> [--fix]
```

* Run on the host computer or the robot
* It will print summary of record count and channels recorded for each tub
* It will print the records that throw an exception while reading
* The optional `--fix` will delete records that have problems

## Augment Tub

This command allows you to perform the data augmentation on a tub or set of tubs directly. The augmentation is also available in training via the `--aug` flag. Preprocessing the tub can speed up the training as the augmentation can take some time. Also you can train with the unmodified tub and the augmented tub joined together. 

Usage:

```bash
donkey tubaugment <tub_path> [--inplace]
```

* Run on the host computer or the robot
* The optional `--inplace` will replace the original tub images when provided. Otherwise `tub_XY_YY-MM-DD` will be copied to a new tub `tub_XX_aug_YY-MM-DD` and the original data remains unchanged


## Histogram

This command will show a pop-up window showing the histogram of record values in a given tub.

> Note: This should be moved from manage.py to donkey command

Usage:

```bash
donkey tubhist <tub_path> --rec=<"user/angle">
```

* Run on the host computer

* When the `--tub` is omitted, it will check all tubs in the default data dir

## Plot Predictions

This command allows you plot steering and throttle against predictions coming from a trained model.

> Note: This should be moved from manage.py to donkey command

Usage:

```bash
donkey tubplot <tub_path> [--model=<model_path>]
```

* This command may be run from `~/mycar` dir
* Run on the host computer
* Will show a pop-up window showing the plot of steering values in a given tub compared to NN predictions from the trained model
* When the `--tub` is omitted, it will check all tubs in the default data dir

## Continuous Rsync

This command uses rsync to copy files from your pi to your host. It does so in a loop, continuously copying files. By default, it will also delete any files
on the host that are deleted on the pi. This allows your PS3 Triangle edits to affect the files on both machines.

Usage:

```bash
donkey consync [--dir = <data_path>] [--delete=<y|n>]
```

* Run on the host computer
* First copy your public key to the pi so you don't need a password for each rsync:

```bash
cat ~/.ssh/id_rsa.pub | ssh pi@<your pi ip> 'cat >> .ssh/authorized_keys'
```

* If you don't have a id_rsa.pub then google how to make one
* Edit your config.py and make sure the fields `PI_USERNAME`, `PI_HOSTNAME`, `PI_DONKEY_ROOT` are setup. Only on windows, you need to set `PI_PASSWD`.
* This command may be run from `~/mycar` dir

## Continuous Train

This command fires off the keras training in a mode where it will continuously look for new data at the end of every epoch.

Usage:

```bash
donkey contrain [--tub=<data_path>] [--model=<path to model>] [--transfer=<path to model>] [--type=<linear|categorical|rnn|imu|behavior|3d>] [--aug]
```

* This command may be run from `~/mycar` dir
* Run on the host computer
* First copy your public key to the pi so you don't need a password for each rsync:

```bash
cat ~/.ssh/id_rsa.pub | ssh pi@<your pi ip> 'cat >> .ssh/authorized_keys'
```

* If you don't have a id_rsa.pub then google how to make one
* Edit your config.py and make sure the fields `PI_USERNAME`, `PI_HOSTNAME`, `PI_DONKEY_ROOT` are setup. Only on windows, you need to set `PI_PASSWD`.
* Optionally it can send the model file to your pi when it achieves a best loss. In config.py set `SEND_BEST_MODEL_TO_PI = True`.
* Your pi drive loop will autoload the weights file when it changes. This works best if car started with `.json` weights like:

```bash
python manage.py drive --model models/drive.json
```

## Joystick Wizard

This command line wizard will walk you through the steps to create a custom/customized controller.  

Usage:

```bash
donkey createjs
```

* Run the command from your `~/mycar` dir
* First make sure the OS can access your device. The utility `jstest` can be useful here. Installed via: `sudo apt install joystick`  You must pass this utility the path to your controller's device.  Typically this is `/dev/input/js0`  However, it if is not, you must find the correct device path and provide it to the utility.  You will need this for the createjs command as well.
* Run the command `donkey createjs` and it will create a file named my_joystick.py in your `~/mycar` folder, next to your manage.py
* Modify myconfig.py to set `CONTROLLER_TYPE="custom"` to use your my_joystick.py controller

## Visualize CNN filter activations

Shows feature maps of the provided image for each filter in each of the convolutional layers in the model provided. Debugging tool to visualize how well feature extraction is performing.

Usage:

```bash
donkey cnnactivations [--tub=<data_path>] [--model=<path to model>]
```

This will open a figure for each `Conv2d` layer in the model.

Example:

```bash
donkey cnnactivations --model models/model.h5 --image data/tub/1_cam-image_array_.jpg
```
