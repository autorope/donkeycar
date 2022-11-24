#!/bin/bash

# quit on any error
set -euxo pipefail

#
# 1. create a projects folder; `mkdir -p  ~/projects`
# 2. change into the projects folder; `cd ~/projects`
# 3. clone donkeycar in projects folder `git clone https://github.com/autorope/donkeycar.git`
# 4. change into the donkeycar project folder; `cd ~/projects/donkeycar`
# 5. run this script; `./install/opi/install.sh`
#

#
# must run from within the donkeycar folder
#
if [ ! -d donkeycar ] || [ ! -f setup.py ]; then
  echo "Error: $0 must be run in the donkeycar project folder."
  exit 99
fi
PROJECT_DIR=$(pwd)



#
# Step 8: Install Dependencies
#
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y build-essential python3 python3-dev python3-pip python3-virtualenv python3-numpy python3-pandas i2c-tools avahi-utils joystick libopenjp2-7-dev libtiff5-dev gfortran libatlas-base-dev libopenblas-dev libhdf5-serial-dev libgeos-dev git ntp



#
# Step 9: (Optional) Install OpenCV Dependencies
#
sudo apt-get install -y libilmbase-dev libopenexr-dev libgstreamer1.0-dev libwebp-dev libatlas-base-dev libavcodec-dev libavformat-dev libswscale-dev 
# sudo apt-get install libjasper-dev libqtgui4 libqt4-test

# gsteamer usb camera support
sudo apt-get install -y libjpeg62-turbo-dev
sudo apt-get install -y cmake gcc g++
sudo apt-get install -y python3-opencv libopencv-dev libprotobuf-c-dev libsdl-dev
if [ ! -d ~/projects/mjpg-streamer/mjpg-streamer-experimental ]; then
  mkdir -p ~/projects/mjpg-streamer
  git clone https://github.com/jacksonliam/mjpg-streamer.git ~/projects/mjpg-streamer/
fi
cd ~/projects/mjpg-streamer/mjpg-streamer-experimental
make
sudo make install
cd ${PROJECT_DIR}



#
# Step 10: Setup Virtual Env
#
if [ -d "env" ]; then
    echo "Removing prior environment"
    rm -rf "env"
fi
python3 -m virtualenv -p python3 env --system-site-packages
echo "source ~/projects/donkeycar/env/bin/activate"
source ~/projects/donkeycar/env/bin/activate



#
# Step 11: Install Donkeycar Python Code
#
pip3 install -e .[opi]

# install tensorflow
pip3 install tflite-runtime



#
# Step 12: (Optional) Install OpenCV
#
sudo apt-get install -y python3-opencv

