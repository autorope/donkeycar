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

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install build-essential python3 python3-dev libhdf5-serial-dev hdf5-tools 
```

##  Step 3: Setup Virtual Env

```bash
python3 -m virtualenv -p python3 env --system-site-packages
echo "source env/bin/activate" >> ~/.bashrc
source ~/.bashrc
```

##  Step 4: Install Donkeycar Python Code

* Change to a dir you would like to use as the head of your projects.

```
mkdir projects
cd projects
```

* Get the latest donkeycar from Github.

```bash
git clone https://github.com/autorope/donkeycar
cd donkeycar
git checkout master
pip install -e .[pi]
pip3 install --extra-index-url https://developer.download.nvidia.com/compute/redist/jp/v42 tensorflow-gpu==1.13.1+nv19.3
```

----

### Next, [create your Donkeycar application](/guide/create_application/).

