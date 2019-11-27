## Install Donkeycar on Mac

![donkey](../assets/logos/apple_logo.jpg)

* Install [miniconda Python 3.7 64 bit](https://conda.io/miniconda.html)

* Install [git 64 bit](https://www.atlassian.com/git/tutorials/install-git)

* Start Terminal

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
conda env create -f install/envs/mac.yml
conda activate donkey
pip install -e .[pc]
```

* Tensorflow GPU

Currently there is no gpu support for [tensorflow on mac](https://www.tensorflow.org/install#install-tensorflow).

* Create your local working dir:

```
donkey createcar --path ~/mycar
```

> Note: After closing the Terminal, when you open it again, you will need to 
> type ```conda activate donkey``` to re-enable the mappings to donkey specific 
> Python libraries


----

### Next let's [install software on Donkeycar](/guide/install_software/#step-2-install-software-on-donkeycar)