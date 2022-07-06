#!/bin/bash

#
# must run from within donkey project folder
#
if [ ! -d donkeycar ] || [ ! -f setup.py ]; then
  echo "Error: install-jp46.sh must be run in the donkeycar project folder."
  exit 255
fi

JP_VERSION=46 install/nano/install.nano.sh

