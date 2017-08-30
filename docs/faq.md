# How do I create my own Raspberry Pi Disk?
If you don't want to use the disk image for the Raspberry Pi you can 
install the packages like this.

1. Setup OS on Raspberry Pi
Follow [these instructions](https://www.raspberrypi.org/learning/software-guide/quickstart/)
to install the Raspbian Jessie operating system using the NOOBS method 
on your SD card.
P
2. ut the SD card into your Raspberry Pi.
3. Power up your Raspberry Pi using the USB cable.
4. Connect to a wifi internet connection. 

##### Install Basic Libraries
Since the Raspberry Pi is not as fast as larger computers, it can take a long time to install python packages (ie. numpy & PIL) using pip. Luckily Adafruit has precompiled these libraries into packages that can be installed via `apt-get`.

1. Open a terminal (Ctrl-Alt-t) and upgrade your system packages.
```
sudo apt-get update
sudo apt-get upgrade
```

2. Install necessary libraries 
```
sudo apt-get install xsel xclip libxml2-dev libxslt-dev libzmq-dev libspatialindex-dev virtualenv
```
3. Pandas & Jupyter Requirements

```
sudo apt-get install python3-lxml python3-h5py python3-numexpr python3-dateutil python3-tz python3-bs4 python3-xlrd python3-tables python3-sqlalchemy python3-xlsxwriter python3-httplib2 python3-zmq 
```
5. Scientific Python
```
sudo apt-get install python3-numpy python3-matplotlib python3-scipy python3-pandas 
```