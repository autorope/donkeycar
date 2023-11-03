#! /bin/bash

set -e

USER=donkey
SRV_SUFFIX=".local" # "" or ".local"
REMOTE_PATH="/home/$USER/donkeycar/" # include trailing /

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LOCAL_PATH="$SCRIPT_DIR/../" # include trailing /

CAR_NAME=$(basename $(pwd))
SRV="${CAR_NAME}${SRV_SUFFIX}"

echo SENDING DONKEYCAR FILES
rsync -rv --progress --partial --delete \
  --exclude=.DS_Store --exclude=.git --exclude=doc --exclude=notebooks --exclude=car_configs \
  "$LOCAL_PATH" "$USER"@"$SRV":"$REMOTE_PATH"
