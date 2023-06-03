#! /bin/bash

set -e

USER=donkey
SRV=pc92.local

# include trailing /
REMOTE_PATH="/home/$USER/donkeycar/"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LOCAL_PATH="$SCRIPT_DIR/../../"

echo SENDING DONKEYCAR FILES
rsync -rv --progress --partial --delete \
  --exclude=.DS_Store --exclude=.git --exclude=doc --exclude=notebooks --exclude=car_configs \
  "$LOCAL_PATH" "$USER"@"$SRV":"${REMOTE_PATH}"
