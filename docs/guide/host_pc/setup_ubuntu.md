# Install Donkeycar on Linux

![donkey](/assets/logos/linux_logo.png)

> Note : tested on Ubuntu 18.04 LTS

* Open the Terminal application.


* Install [miniconda Python 3.7 64 bit](https://conda.io/miniconda.html). 

```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash ./Miniconda3-latest-Linux-x86_64.sh
```

* Change to a dir you would like to use as the head of your projects.

```
mkdir projects
cd projects
```

* Get the latest donkeycar from Github.

```
git clone https://github.com/autorope/donkeycar
cd donkeycar
git checkout master
```


* If this is not your first install, update Conda and remove old donkey
```
conda update -n base -c defaults conda
conda env remove -n donkey
```

* Create the Python anaconda environment

```
conda env create -f install/envs/ubuntu.yml
conda activate donkey
pip install -e .[pc]
```

* Optionall Install Tensorflow GPU

You should have an NVidia GPU with the latest drivers. Conda will handle installing the correct cuda and cuddn libraries for the version of tensorflow you are using.

```
conda install tensorflow-gpu
```

* Create your local working dir:

```
donkey createcar --path ~/mycar
```

> Note: After closing the Anaconda Prompt, when you open it again, you will need to 
> type ```conda activate donkey``` to re-enable the mappings to donkey specific 
> Python libraries

----

### Next let's [install software on Donkeycar](/guide/install_software/#step-2-install-software-on-donkeycar)