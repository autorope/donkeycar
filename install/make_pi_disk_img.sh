sudo apt update -y
sudo apt upgrade -y
sudo rpi-update -y
sudo apt install build-essential python3-dev python3-distlib python3-setuptools  python3-pip python3-wheel -y
sudo apt install libzmq-dev -y
sudo apt install xsel xclip -y

#remove python2
sudo apt-get remove python2.7
sudo apt-get autoremove



#opencv
#instructions from:https://raspberrypi.stackexchange.com/questions/69169/how-to-install-opencv-on-raspberry-pi-3-in-raspbian-jessie
sudo apt-get install build-essential git cmake pkg-config
sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev
sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt-get install libxvidcore-dev libx264-dev
#sudo apt-get install libgtk2.0-dev #not used no interface needed
sudo apt-get install libatlas-base-dev gfortran

git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git

#dependencies for pandas
sudo apt install libxml2-dev python3-lxml -y
sudo apt install libxslt-dev


sudo apt install virtualenv -y
virtualenv env --system-site-packages --python python3
echo '#start env' >> ~/.bashrc
echo 'source ~/env/bin/activate' >> ~/.bashrc
source ~/.bashrc

pip install pandas
sudo apt-get python3-numpy -y
sudo apt install python3-pandas -y
sudo apt install python3-matplotlib