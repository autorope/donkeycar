#! /bin/bash

set -e

USER=donkey
SRV=pc94.local

# include trailing /
REMOTE_PATH="/home/$USER/car/"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LOCAL_PATH="${SCRIPT_DIR}/"

echo "SENDING"
rsync -rv --progress --partial --delete \
  --exclude=.DS_Store --exclude=data --exclude=logs --exclude=.git --exclude=models_trt \
  "$LOCAL_PATH" "$USER"@"$SRV":"${REMOTE_PATH}"

echo
echo "RECEIVING DATA AND LOGS"
rsync -rv --progress --partial --include=logs/*** --include=data/*** --exclude=* "$USER"@"$SRV":"${REMOTE_PATH}" "$LOCAL_PATH"
