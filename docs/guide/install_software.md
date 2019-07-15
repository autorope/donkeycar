#Install Software

* [Overview](#Overview)
* Software:
    * [Step 1: Install Software on Host PC](install_software.md#step-1-install-software-on-host-pc)
    * [Step 2: Install Software on Donkeycar](install_software.md#step-2-install-software-on-donkeycar)
* [Create Donkeycar Application](/guide/create_application/)

## Overview

Donkeycar has components to install on a host PC. This can be a laptop, or desktop machine. The machine doesn't have to be powerful, but it will benefit from faster cpu, more ram, and an NVidia GPU. An SSD hard drive will greatly impact your training times.

Donkeycar software components need to be installed on the robot platform of your choice. Raspberry Pi and Jetson Nano have setup docs. But it has been known to work on Jetson TX2, Friendly Arm SBC, or almost any Debian based SBC ( single board computer ).

After install, you will create the Donkeycar application from a template. This contains code that is designed for you to customize for your particular case. Don't worry, we will get you started with some useful defaults. 

Next we will train the Donkeycar to drive on it's own based on your driving style! This uses a supervised learning technique often referred to as behavioral cloning.

<iframe width="560" height="315" src="https://www.youtube.com/embed/BQY9IgAxOO0" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

This is not the only method for getting your Donkeycar to drive itself. But it requires the least amount of hardware and least technical knowledge. Then you can explore other techniques in this Ai mobile laboratory called Donkeycar!

## Step 1: Install Software on Host PC

When controlling your Donkey via behavioral cloning, you will need to setup a host pc to train your machine learning model from the data collected on the robot. Choose a setup that matches your computer OS.


* Setup [Linux Host PC](host_pc/setup_ubuntu.md)
![donkey](/assets/logos/linux_logo.png)
* Setup [Windows Host PC](host_pc/setup_windows.md)
![donkey](/assets/logos/windows_logo.png)
* Setup [Mac Host PC](host_pc/setup_mac.md)
![donkey](/assets/logos/apple_logo.jpg)


# Step 2: Install Software On Donkeycar

This guide will help you to setup the software to run Donkeycar on your Raspberry Pi or Jetson Nano. Choose a setup that matches your SBC type. (SBC = single board computer)

* Setup [RaspberryPi](robot_sbc/setup_raspberry_pi.md)
![donkey](/assets/logos/rpi_logo.png)

* Setup [Jetson Nano](robot_sbc/setup_jetson_nano.md)
![donkey](/assets/logos/nvidia_logo.png)


## Next: [Create Your Donkeycar Application](/guide/create_application/).