#create a python virtualenv (2 min)
sudo apt install virtualenv -y
virtualenv ~/env --system-site-packages --python python3
echo '#start env' >> ~/.bashrc
echo 'source ~/env/bin/activate' >> ~/.bashrc
source ~/env/bin/activate