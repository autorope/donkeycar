# Script to install everything needed for donkeycar except the donkeycar library

#standard updates (5 min)
sudo apt update -y
sudo apt upgrade -y
sudo rpi-update -y

#helpful libraries (2 min)
sudo apt install build-essential python3-dev python3-distlib python3-setuptools  python3-pip python3-wheel -y

sudo apt-get install git cmake pkg-config -y
sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev -y
sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev -y
sudo apt-get install libxvidcore-dev libx264-dev -y
sudo apt-get install libatlas-base-dev gfortran -y

sudo apt install libzmq-dev -y
sudo apt install xsel xclip -y
sudo apt install python3-h5py -y

#install numpy and pandas (3 min)
sudo apt install libxml2-dev python3-lxml -y
sudo apt install libxslt-dev -y

#remove python2 (1 min)
sudo apt-get remove python2.7 -y
sudo apt-get autoremove -y

#install redis-server (1 min)
sudo apt install redis-server -y

#create a python virtualenv (2 min)
sudo apt install virtualenv -y
virtualenv ~/env --system-site-packages --python python3
echo '#start env' >> ~/.bashrc
echo 'source ~/env/bin/activate' >> ~/.bashrc
source ~/env/bin/activate


#make sure the virtual environment is active
source ~/env/bin/activate

# install pandas and numpy and Adafruit CircuitPython
pip install pandas #also installs numpy
pip install adafruit-circuitpython-lis3dh

pip install tensorflow==1.9