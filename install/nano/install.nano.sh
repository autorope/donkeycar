#!/bin/bash

#
# must run from within donkey project folder
#
if [ ! -d donkeycar ] || [ ! -f setup.py ]; then
  echo "Error: install.nano.sh must be run in the donkeycar project folder."
  exit 255
fi

#
# JP_VERSION must be defined
#
if [ "$JP_VERSION" == "" ]; then
  echo "Error: JP_VERSION must be defined.  45 for 4.5.x, 46 for 4.6.x, etc."
  echo "Usage:   JP_VERSION=## $0"
  echo "Example for Jetpack 4.5.x: JP_VERSION=45 $0"
  echo "Example for Jetpack 4.6.x: JP_VERSION=46 $0"
  exit 255
fi

# remember project folder
CWD=$(pwd)

# make sure we have xlocale.h to build h5py
if [ ! -f /usr/include/xlocale.h ]; then
  ln -s /usr/include/locale.h /usr/include/xlocale.h
fi


#
# Step 2: Free up the serial port
#
# sudo usermod -aG dialout <your username>
# sudo systemctl disable nvgetty


#
# Step 3: Install System-Wide Dependencies
#
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y libhdf5-serial-dev hdf5-tools libhdf5-dev zlib1g-dev zip libjpeg8-dev liblapack-dev libblas-dev gfortran
sudo apt-get install -y python3-dev python3-pip
sudo apt-get install -y libxslt1-dev libxml2-dev libffi-dev libcurl4-openssl-dev libssl-dev libpng-dev libopenblas-dev
sudo apt-get install -y git nano
sudo apt-get install -y openmpi-doc openmpi-bin libopenmpi-dev libopenblas-dev

# required for pip install h5py=3.1.0
sudo apt install python3-h5py


#
# Step 4: Setup Virtual Environment
#
deactivate
rm -rf ~/env
pip3 install virtualenv
python3 -m virtualenv -p python3 ~/env --system-site-packages
# echo "source env/bin/activate" >> ~/.bashrc
source ~/env/bin/activate


#
# Step 5: Setup Python Dependencies
#
pip3 install -U pip testresources setuptools==49.6
pip3 install -U futures==3.1.1 protobuf==3.12.2 pybind11==2.5.0
pip3 install -U cython==0.29.21 pyserial
pip3 install -U future==0.18.2 mock==4.0.2 h5py==2.10.0 keras_preprocessing==1.1.2 keras_applications==1.0.8 gast==0.3.3
pip3 install -U absl-py==0.9.0 py-cpuinfo==7.0.0 psutil==5.7.2 portpicker==1.3.1 six requests==2.24.0 astor==0.8.1 termcolor==1.1.0 wrapt==1.12.1 google-pasta==0.2.0
pip3 install -U --no-deps numpy==1.19.4 future==0.18.2 mock==3.0.5 keras_preprocessing==1.1.2 keras_applications==1.0.8 gast==0.4.0 protobuf pybind11 cython pkgconfig
# build h5py from source
pip3 install --no-binary :h5py:  h5py==3.1.0
pip3 install -U gdown==3.10.1

#
# This will install tensorflow as a system package
# based on the jetpack version that is running
#
pip3 install --pre --extra-index-url "https://developer.download.nvidia.com/compute/redist/jp/v${JP_VERSION}" tensorflow

#
# install pytorch
#
sudo apt-get install -y libjpeg-dev zlib1g-dev libpython3-dev libavcodec-dev libavformat-dev libswscale-dev
mkdir -p ~/projects; cd ~/projects
wget https://nvidia.box.com/shared/static/p57jwntv436lfrd78inwl7iml6p13fzh.whl
mv p57jwntv436lfrd78inwl7iml6p13fzh.whl torch-1.8.0-cp36-cp36m-linux_aarch64.whl
pip3 install torch-1.8.0-cp36-cp36m-linux_aarch64.whl
rm torch-1.8.0-cp36-cp36m-linux_aarch64.whl
git clone -b v0.9.0 https://github.com/pytorch/vision torchvision
cd torchvision
python setup.py install
# restore the project folder
cd "$CWD"

#
# Step 6: Install Donkeycar Python Code
#
pip install -e .[nano]


echo "To activate the donkey environment: 'source ~/env/bin/activate'"

