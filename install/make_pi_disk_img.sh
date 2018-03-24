# Manually make sure the camera and I2C are enabled.
sudo rasp-config


#standard updates (5 min)
sudo apt update -y
sudo apt upgrade -y
sudo rpi-update -y

#helpful libraries (2 min)
sudo apt install build-essential python3-dev python3-distlib python3-setuptools  python3-pip python3-wheel -y
sudo apt install libzmq-dev -y
sudo apt install xsel xclip -y


#remove python2 (1 min)
sudo apt-get remove python2.7
sudo apt-get autoremove


#create a python virtualenv (2 min)
sudo apt install virtualenv -y
virtualenv env --system-site-packages --python python3
echo '#start env' >> ~/.bashrc
echo 'source ~/env/bin/activate' >> ~/.bashrc
source ~/.bashrc


#install numpy and pandas (3 min)
sudo apt install libxml2-dev python3-lxml -y
sudo apt install libxslt-dev
pip install pandas


#install opencv (1 hour)
#instructions from:https://raspberrypi.stackexchange.com/questions/69169/how-to-install-opencv-on-raspberry-pi-3-in-raspbian-jessie
sudo apt-get install build-essential git cmake pkg-config
sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev
sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt-get install libxvidcore-dev libx264-dev
#sudo apt-get install libgtk2.0-dev #not used no interface needed
sudo apt-get install libatlas-base-dev gfortran

git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git
pip install numpy
cd ~/opencv
mkdir build
cd build
cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D INSTALL_C_EXAMPLES=OFF \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib/modules \
    -D BUILD_EXAMPLES=OFF ..
make -j4
sudo make install
sudo ldconfig



#install tensorflow (5 min)
wget https://github.com/lhelontra/tensorflow-on-arm/releases/download/v1.5.0/tensorflow-1.5.0-cp35-none-linux_armv7l.whl
pip install tensorflow-1.5.0-cp35-none-linux_armv7l.whl
rm tensorflow-1.5.0-cp35-none-linux_armv7l.whl


#install donkey (1 min)
mkdir code
cd code
git clone https://github.com/wroscoe/donkey.git
pip install -e donkey/[pi]


#remove dev libraries...
sudo apt-get purge lib*-dev

#reinstal only needed libs
sudo apt-get install libatlas-base-dev libtiff5 libopenjp2-7-dev


#install redis-server (1 min)
sudo apt install redis-server
