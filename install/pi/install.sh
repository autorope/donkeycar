# Script to install everything needed for donkeycar except the donkeycar library


# Get witch Pi version
echo "Enter the Pi number (3 or 0)"
read pi_num
if  [ $pi_num == 3 ]; then
  echo "installing for Pi 3."
  tf_file=tensorflow-1.8.0-cp35-none-linux_armv7l.whl
elif [ $pi_num == 0 ]; then
  echo "installing for Pi Zero."
  tf_file=tensorflow-1.8.0-cp35-none-linux_armv6l.whl
else
  echo "Only Pi 3 and Pi Zero are supported."
  exit 1
fi


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

sudo bash make_virtual_env.sh


#create a python virtualenv (2 min)
sudo apt install virtualenv -y
virtualenv ~/env --system-site-packages --python python3
echo '#start env' >> ~/.bashrc
echo 'source ~/env/bin/activate' >> ~/.bashrc
source ~/env/bin/activate


#make sure the virtual environment is active
source ~/env/bin/activate

# install pandas and numpy
pip install pandas #also installs numpy


#install tensorflow (5 min)
echo "Installing Tensorflow"
wget https://github.com/lhelontra/tensorflow-on-arm/releases/download/v1.8.0/${tf_file}
pip install ${tf_file}
rm ${tf_file}