#!/usr/bin/env bash

# Folder that will contain all the files
# that were on the rsynced folder with the Raspbery Pi 3
RSYNC_FOLDER=~/ricar

# Uninstall the old package
pip uninstall donkeycar

# Reinstall this project
pip install -e .


# Move the manage.py file, it may be updated
echo "Copying manage.py to " $RSYNC_FOLDER
cp manage.py $RSYNC_FOLDER

