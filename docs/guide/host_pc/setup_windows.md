## Install Donkeycar on Windows

![donkey](/assets/logos/windows_logo.png)

* Install [miniconda Python 3.7 64 bit](https://conda.io/miniconda.html).

* Open the Anaconda prompt window via Start Menu | Anaconda 64bit | Anaconda Prompt

* type `git`. If the command is not found, then install [git 64 bit](https://git-scm.com/download/win)


* Change to a dir you would like to use as the head of your projects.

```
mkdir projects
cd projects
```

* Get the latest donkey from Github.

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
conda env create -f install\envs\windows.yml
conda activate donkey
pip install -e .[pc]
```

* Optionally Install Tensorflow GPU

If you have an NVidia card, you should update to the lastest drivers and [install Cuda SDK](https://www.tensorflow.org/install/gpu#windows_setup). 

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