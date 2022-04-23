#
# This script will create an standard python environment
# in the donkeycar project folder.  This is an alternative
# to using conda, as the conda environment installation
# may make many many hours to resolve on the Mac.
#
# After running this script you will have an environment
# folder in the donkeycar project folder.  To activate the
# environment from the donkeycar folder;
# ```
#   source env/bin/activate
# ```
#
# dependencies:
# - python=3.7
# -  pip
#

#
# must run from within donkey project folder
#
if [ ! -d donkeycar ] || [ ! -f setup.py ]; then
  echo "Error: $0 must be run in the donkeycar project folder."
  exit 255
fi

# remember project folder
CWD=$(pwd)

python3 -m venv env
source env/bin/activate

# development tools
pip3 install pylint==2.8.3
pip3 install pytest pytest-cov codecov

#
# data formats
#
pip3 install --no-binary :h5py:  h5py==3.1.0
pip3 install pyyaml

# 
# telemetry
#
pip3 install paho-mqtt

#
# web server for client
#
pip3 install tornado requests

#
# console
#
pip3 install progress PrettyTable pyfiglet
pip3 install docopt
pip3 install readchar

#
# python language utilities
#
pip3 install mypy==0.812
pip3 install psutil
pip3 install typing_extensions

# pip controller
pip3 install simple-pid

#
# graphics
#
pip3 install imageio==2.10.5
pip3 install opencv-python==4.4.0.46
pip3 install pillow
pip3 install imgaug
pip3 install plotly
pip3 install moviepy

#
# data science
#
pip3 install -U --no-deps numpy==1.19.4
pip3 install matplotlib pandas

#
# training models
#
pip3 install tensorflow==2.5.3
pip3 install git+https://github.com/autorope/keras-vis.git
pip3 install pytorch=1.7.1
pip3 install torchvision
pip3 install torchaudio
pip3 install pytorch-lightning
pip3 install fastai


#
# gps
#
pip3 install pyserial utm pynmea2

#
# donkey ui
#
pip3 install kivy==2.0.0

#
# install donkey command
#
pip3 install -e .[pc]
