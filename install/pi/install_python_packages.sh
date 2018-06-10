#make sure the virtual environment is active
source ~/.bashrc

# install pandas and numpy
pip install pandas #also installs numpy


#install tensorflow (5 min)
tf_file=tensorflow-1.8.0-cp35-none-linux_armv7l.whl
wget https://github.com/lhelontra/tensorflow-on-arm/releases/download/v1.8.0/${tf_file}
pip install ${tf_file}
rm ${tf_file}


