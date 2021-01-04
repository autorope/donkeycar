# Get Your Jetson Nano Working

![donkey](/assets/logos/nvidia_logo.png)

* [Step 1: Flash Operating System](#step-1-flash-operating-system)
* [Step 2: Install Dependencies](#step-2-install-dependencies)
* [Step 3: Setup Virtual Env](#step-3-setup-virtual-env)
* [Step 4: Install Donkeycar Python Code](#step-4-install-donkeycar-python-code)
* Then [Create your Donkeycar Application](/guide/create_application/)

## Step 1: Flash Operating System

Visit the official [Nvidia Jetson Nano Getting Started Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit#prepare). Work through the __Prepare for Setup__, __Writing Image to the microSD Card__, and __Setup and First Boot__ instructions, then return here.

## Step 2: Install Dependencies

ssh into your vehicle. Use the the terminal for Ubuntu or Mac. [Putty](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) for windows.

Note: you can either proceed with this tutorial, or if you have Jetpack 4.4 installed, you can use a script to automate the setup. The script is located in `donkeycar/install/nano/install-jp44.sh`. You will need to edit line #3 of the script and replace the default password with your password. This script will install all Git repositories into a ~/projects directory. If you wish to use a different directory, you will need to change this as well (replace all instances of ~/projects with your desired folder path). 

First install some packages with `apt-get`.
```bash
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y libhdf5-serial-dev hdf5-tools libhdf5-dev zlib1g-dev zip libjpeg8-dev liblapack-dev libblas-dev gfortran
sudo apt-get install -y python3-dev python3-pip
sudo apt-get install -y libxslt1-dev libxml2-dev libffi-dev libcurl4-openssl-dev libssl-dev libpng-dev libopenblas-dev
sudo apt-get install -y git
sudo apt-get install -y openmpi-doc openmpi-bin libopenmpi-dev libopenblas-dev
```

Next, you will need to install packages with `pip`:
```bash
sudo -H pip3 install -U pip testresources setuptools
sudo -H pip3 install -U futures==3.1.1 protobuf==3.12.2 pybind11==2.5.0
sudo -H pip3 install -U cython==0.29.21
sudo -H pip3 install -U numpy==1.19.0
sudo -H pip3 install -U future==0.18.2 mock==4.0.2 h5py==2.10.0 keras_preprocessing==1.1.2 keras_applications==1.0.8 gast==0.3.3
sudo -H pip3 install -U grpcio==1.30.0 absl-py==0.9.0 py-cpuinfo==7.0.0 psutil==5.7.2 portpicker==1.3.1 six requests==2.24.0 astor==0.8.1 termcolor==1.1.0 wrapt==1.12.1 google-pasta==0.2.0
sudo -H pip3 install -U scipy==1.4.1
sudo -H pip3 install -U pandas==1.0.5
sudo -H pip3 install -U gdown

# This will install tensorflow as a system package
sudo -H pip3 install --pre --extra-index-url https://developer.download.nvidia.com/compute/redist/jp/v44 tensorflow==2.2.0+nv20.6
```

Finally, you can install PyTorch:
```bash
# Install PyTorch v1.7 - torchvision v0.8.1
wget https://nvidia.box.com/shared/static/wa34qwrwtk9njtyarwt5nvo6imenfy26.whl -O torch-1.7.0-cp36-cp36m-linux_aarch64.whl
sudo -H pip3 install ./torch-1.7.0-cp36-cp36m-linux_aarch64.whl

# Install PyTorch Vision
sudo apt-get install libjpeg-dev zlib1g-dev libpython3-dev libavcodec-dev libavformat-dev libswscale-dev

# You can replace the following line with wherever you want to store your Git repositories
mkdir -p ~/projects; cd ~/projects
git clone --branch v0.8.1 https://github.com/pytorch/vision torchvision
cd torchvision
export BUILD_VERSION=0.8.1
sudo python3 setup.py install
```

Optionally, you can install RPi.GPIO clone for Jetson Nano from [here](https://github.com/NVIDIA/jetson-gpio). This is not required for default setup, but can be useful if using LED or other GPIO driven devices.

##  Step 3: Setup Virtual Env

```bash
pip3 install virtualenv
python3 -m virtualenv -p python3 env --system-site-packages
echo "source env/bin/activate" >> ~/.bashrc
source ~/.bashrc
```

##  Step 4: Install Donkeycar Python Code

* Change to a dir you would like to use as the head of your projects.

```bash
mkdir -p ~/projects; cd ~/projects
```

* Get the latest donkeycar from Github.

```bash
git clone https://github.com/autorope/donkeycar
cd donkeycar
git checkout master
pip install -e .[nano]
```

##  Step 5: Install PyGame (Optional)

If you plan to use a USB camera, you will also want to setup pygame:

```bash
sudo apt-get install python-dev libsdl1.2-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsdl1.2-dev libsmpeg-dev python-numpy subversion libportmidi-dev ffmpeg libswscale-dev libavformat-dev libavcodec-dev libfreetype6-dev

pip install pygame

```

Later on you can add the `CAMERA_TYPE="WEBCAM"` in myconfig.py.

----

### Next, [create your Donkeycar application](/guide/create_application/).
