# Get Your Jetson Nano Working

![donkey](/assets/logos/nvidia_logo.png)

- [Get Your Jetson Nano Working](#get-your-jetson-nano-working)
	- [Step 1: Flash Operating System](#step-1-flash-operating-system)
	- [Step 2: Install Dependencies](#step-2-install-dependencies)
	- [Step 3: Setup Virtual Env](#step-3-setup-virtual-env)
	- [Step 4: Install OpenCV](#step-4-install-opencv)
		- [Next, create your Donkeycar application.](#next-create-your-donkeycar-application)

## Step 1: Flash Operating System

Download our pre-built image
[Download Jetson Nano donkey car 3.2 image](https://www.dropbox.com/s/uzvsmf6j3s9fqw8/jetson_nano_dk_302.zip?dl=0)



You can skip directly


Visit the official [Nvidia Jetson Nano Getting Started Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit#prepare). Work through the __Prepare for Setup__, __Writing Image to the microSD Card__, and __Setup and First Boot__ instructions, then return here.

## Step 2: Install Dependencies

ssh into your vehicle. Use the the terminal for Ubuntu or Mac. [Putty](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) for windows.

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install build-essential python3 python3-dev python3-pip python3-pandas python3-opencv python3-h5py libhdf5-serial-dev hdf5-tools nano ntp
```

Optionally, you can install RPi.GPIO clone for Jetson Nano from [here](https://github.com/NVIDIA/jetson-gpio). This is not required for default setup, but can be useful if using LED or other GPIO driven devices.

##  Step 3: Setup Virtual Env

```bash
pip3 install virtualenv
python3 -m virtualenv -p python3 env --system-site-packages
echo "source env/bin/activate" >> ~/.bashrc
source ~/.bashrc
```

## Step 4: Install OpenCV

To install Open CV on the Jetson Nano, you need to build it from source. Building OpenCV from source is going to take some time, so buckle up. If you get stuck, [here](https://www.pyimagesearch.com/2018/08/15/how-to-install-opencv-4-on-ubuntu/) is another great resource which will help you compile OpenCV.

> Note: In some cases Python OpenCV may already be installed in your disc image. If the file exists, you can optionally copy it to your environment rather than build from source. Nvidia has said they will drop support for this, so longer term we will probably be building it. If this works:
>
> ```
> mkdir ~/mycar
> cp /usr/lib/python3.6/dist-packages/cv2.cpython-36m-aarch64-linux-gnu.so ~/mycar/
> cd ~/mycar
> python -c "import cv2"
> ```
>
> Then you have a working version and can skip this portion of the guide.
> However, following the swapfile portion of this guide has made performance more predictable and solves memory thrashing.

The first step in building OpenCV is to define swap space on the Jetson Nano. The Jetson Nano has `4GB` of RAM. This is not sufficient to build OpenCV from source. Therefore we need to define swap space on the Nano to prevent memory thrashing.

```bash
# Allocates 4G of additional swap space at /var/swapfile
sudo fallocate -l 4G /var/swapfile
# Permissions
sudo chmod 600 /var/swapfile
# Make swap space
sudo mkswap /var/swapfile
# Turn on swap
sudo swapon /var/swapfile
# Automount swap space on reboot
sudo bash -c 'echo "/var/swapfile swap swap defaults 0 0" >> /etc/fstab'
# Reboot
sudo reboot
```

Now you should have enough swap space to build OpenCV. Let's setup the Jetson Nano with the pre-requisites to build OpenCV.

```bash
# Update
sudo apt-get update
sudo apt-get upgrade
# Pre-requisites
sudo apt-get install build-essential cmake unzip pkg-config
sudo apt-get install libjpeg-dev libpng-dev libtiff-dev
sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt-get install libxvidcore-dev libx264-dev
sudo apt-get install libgtk-3-dev
sudo apt-get install libatlas-base-dev gfortran
sudo apt-get install python3-dev
```

Now you should have all the pre-requisites you need.  So, lets go ahead and download the source code for OpenCV.

```bash
# Create a directory for opencv
mkdir -p projects/cv2
cd projects/cv2

# Download sources
wget -O opencv.zip https://github.com/opencv/opencv/archive/4.1.0.zip
wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/4.1.0.zip

# Unzip
unzip opencv.zip
unzip opencv_contrib.zip

# Rename
mv opencv-4.1.0 opencv
mv opencv_contrib-4.1.0 opencv_contrib
```

Let's get our virtual environment (`env`) ready for OpenCV.

```bash
# Install Numpy
pip install numpy
```

Now let's setup `CMake` correctly so it generates the correct OpenCV bindings for our virtual environment.

```bash
# Create a build directory
cd projects/cv2
mkdir build
cd build

# Setup CMake
cmake -D CMAKE_BUILD_TYPE=RELEASE \
	-D CMAKE_INSTALL_PREFIX=/usr/local \
	-D INSTALL_PYTHON_EXAMPLES=ON \
	-D INSTALL_C_EXAMPLES=OFF \
	-D OPENCV_ENABLE_NONFREE=ON \
	# Contrib path
	-D OPENCV_EXTRA_MODULES_PATH=~/projects/cv2/opencv_contrib/modules \
	# Your virtual environment's Python executable
	# You need to specify the result of echo $(which python)
	-D PYTHON_EXECUTABLE=~/env/bin/python \
	-D BUILD_EXAMPLES=ON ../opencv
```

The `cmake` command should show a summary of the configuration. Make sure that the `Interpreter` is set to the Python executable associated to *your* virtualenv.  Note: there are several paths in the CMake setup, make sure they match where you downloaded and saved the OpenCV source.

To compile the code from the `build` folder issue the following command.

```bash
mkdir -p ~/projects; cd ~/projects
```

* Get the latest donkeycar from Github.

```bash
git clone https://github.com/autorope/donkeycar
cd donkeycar
git checkout master
pip install -e .[nano]
pip install --extra-index-url https://developer.download.nvidia.com/compute/redist/jp/v42 tensorflow-gpu==1.13.1+nv19.3
```

Note: This last command can take some time to compile grpcio.

The native library should now be installed in a location that looks like `/usr/local/lib/python3.6/site-packages/cv2/python-3.6/cv2.cpython-36m-xxx-linux-gnu.so`.

If you plan to use a USB camera, you will also want to setup pygame:

```bash
sudo apt-get install python-dev libsdl1.2-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsdl1.2-dev libsmpeg-dev python-numpy subversion libportmidi-dev ffmpeg libswscale-dev libavformat-dev libavcodec-dev libfreetype6-dev

pip install pygame

```

Later on you can add the `CAMERA_TYPE="WEBCAM"` in myconfig.py.

----

### Next, [create your Donkeycar application](/guide/create_application/).
