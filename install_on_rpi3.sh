#!/usr/bin/env bash

# Folder that will contain all the files
# that were on the rsynced folder with the Raspbery Pi 3
RSYNC_FOLDER=~/ricar

# Uninstall the old package
pip uninstall donkeycar

# Get the latest code 
git pull origin master

# Build the latest changes
python setup.py build

# Reinstall this project
pip install -e .

# Move the manage.py file, it may be updated
echo "Copying manage.py to " $RSYNC_FOLDER
cp manage.py $RSYNC_FOLDER

