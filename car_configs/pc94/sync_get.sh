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
  --exclude=.DS_Store  --exclude=logs --exclude=.git \
  "$LOCAL_PATH" "$USER"@"$SRV":"${REMOTE_PATH}"
