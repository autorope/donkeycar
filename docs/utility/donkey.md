# Donkey Command-line Utilities

The `donkey` command is created when you install the donkeycar python package. This is a python script that adds some important functionality. The operations here are vehicle independant, and should work on any hardware configuration.

## Create Car

This command creates a new dir which will contain the files needed to run and train your robot.

Usage:
```bash
donkey createcar --path <dir> [--overwrite] [--template <donkey2>]
```

* This command may be run from any dir
* Run on the host computer or the robot
* It uses the --path as the destination dir to create. If .py files exist there, it will not overwrite them, unless the optional --overwrite is used. 
* The optional --template will specify the template file to start from. For a list of templates, see the `donkeycar/templates` dir

## Find Car

This command attempts to locate your car on the local network using nmap.

Usage:
```bash
donkey findcar
```

* This command may be run from any dir
* Run on the host computer
* Prints the host computer ip address and the car ip address if found
* Requires the nmap utlity:
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

* This command may be run from any dir
* Run on the host computer
* Opens the PWM chanel specified by --channel
* Type integer values to specify PWM values and hit enter
* Hit `Ctrl + C` to exit


## Make Movie from Tub

This command allows you to create a movie file from the images in a Tub.

Usage:
```bash
donkey makemovie --tub=<dir> [--out=<tub_movie.mp4>] [--config=<config.py>]
```

* This command may be run from ~/d2 dir
* Run on the host computer or the robot
* Uses the image records from --tub dir path given
* Creates a movie given by --out. Codec is infered from file extension. Default: tub_movie.mp4
* Optional argument to specify a different config.py other than default: config.py



## Check Tub

This command allows you to see how many records are contained in any/all tubs. It will also open each record and ensure that the data is readable and intact. If not, it will allow you to remove corrupt records.

> Note: This should be moved from manage.py to donkey command

Usage:
```bash
python manage.py check [--tub <tubdir>] [--fix]
```

* This command may be run from ~/d2 dir
* Run on the host computer or the robot
* When the --tub is ommited, it will check all tubs in the default data dir
* It will print summary of record count and channels recorded for each tub
* It will print the records that throw an exception while reading
* The optional --fix will delte records that have problems

## Analyze - Histogram

This command allows you to see various stats about your data.

> Note: This should be moved from manage.py to donkey command

Usage:
```bash
python manage.py analyze [--tub <tubdir>] --op=histogram --rec=<"user/angle">
```

* This command may be run from ~/d2 dir
* Run on the host computer
* Will show a pop-up window showing the histogram of steering values in a given tub
* When the --tub is ommited, it will check all tubs in the default data dir
* In the future hopefully more analysis types can be added

## Simulation Server

This command allows you serve steering and throttle controls to a simulated vehicle using the [Donkey Simulator](/guide/simulator.md).

Usage:
```bash
donkey sim --model=<model_path> [--type=<linear|categorical>] [--top_speed=<speed>] [--config=<config.py>]
```

* This command may be run from ~/d2 dir
* Run on the host computer
* Uses the model to make predictions based on images and telemetry from the simulator
* --type can specify whether the model needs angle output to be treated as categorical
* top speed can be modified to ascertain stablity at different goal speeds
