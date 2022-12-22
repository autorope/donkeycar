#!/bin/bash -e

#password='jetson'
# Get the full dir name of this script
#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Keep updating the existing sudo time stamp
#sudo -v
#while true; do sudo -n true; sleep 120; kill -0 "$$" || exit; done 2>/dev/null &

########################################
# Install DonkeyCar
########################################
# Install ubuntu modules
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y libhdf5-serial-dev hdf5-tools libhdf5-dev zlib1g-dev zip libjpeg8-dev liblapack-dev libblas-dev gfortran
sudo apt-get install -y python3-dev python3-pip
sudo apt-get install -y libxslt1-dev libxml2-dev libffi-dev libcurl4-openssl-dev libssl-dev libpng-dev libopenblas-dev
sudo apt-get install -y git nano
sudo apt-get install -y openmpi-doc openmpi-bin libopenmpi-dev libopenblas-dev

# Install python modules
sudo pip3 install -U pip testresources setuptools
sudo ln -s /usr/include/locale.h /usr/include/xlocale.h
sudo pip3 install -U futures protobuf==3.19.6 pybind11 cython pyserial 
sudo pip3 install -U numpy==1.19.4 future mock h5py keras_preprocessing keras_applications gast==0.2.1 
sudo pip3 install -U grpcio absl-py py-cpuinfo psutil portpicker wrapt==1.12.1 six requests 
sudo pip3 install -U astor termcolor google-pasta scipy pandas gdown pkgconfig packaging

# Install tensorflow
sudo pip3 install --extra-index-url https://developer.download.nvidia.com/compute/redist/jp/v461 tensorflow


########################################
# Install PyTorch v1.7 - torchvision v0.8.1
# pytorch 1.6.0-rc2
# https://forums.developer.nvidia.com/t/pytorch-for-jetson-nano-version-1-5-0-now-available/72048/392
#wget https://nvidia.box.com/shared/static/wa34qwrwtk9njtyarwt5nvo6imenfy26.whl -O torch-1.7.0-cp36-cp36m-linux_aarch64.whl
#sudo -H pip3 install ./torch-1.7.0-cp36-cp36m-linux_aarch64.whl

# Install PyTorch Vision
#sudo apt-get install libjpeg-dev zlib1g-dev libpython3-dev libavcodec-dev libavformat-dev libswscale-dev
#mkdir -p ~/projects; cd ~/projects
#git clone --branch v0.8.1 https://github.com/pytorch/vision torchvision
#cd torchvision
#export BUILD_VERSION=0.8.1
#sudo python3 setup.py install


# Create virtual enviroment
pip3 install virtualenv
python3 -m virtualenv -p python3 ~/.virtualenv/donkeycar --system-site-packages
echo "source ~/.virtualenv/donkeycar/bin/activate" >> ~/.bashrc
# "source ~/.virtualenv/donkeycar/bin/activate" in the shell script
. ~/.virtualenv/donkeycar/bin/activate


# Install DonkeyCar as user package
mkdir ~/github
cd ~/github
git clone https://github.com/roboracingleague/donkeycar
cd donkeycar
git checkout main
pip install -e .[nano]

# https://github.com/keras-team/keras-tuner/issues/317
echo "export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1" >> ~/.bashrc
#export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1