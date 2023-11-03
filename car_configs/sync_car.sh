#! /bin/bash

set -e

USER=donkey
SRV_SUFFIX=".local" # "" or ".local"
REMOTE_PATH="/home/$USER/car"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
TEMPLATE_PATH="${SCRIPT_DIR}/../donkeycar/templates"
LOCAL_PATH=$(pwd)

CAR_NAME=$(basename $LOCAL_PATH)
SRV="${CAR_NAME}${SRV_SUFFIX}"

TEMPLATE_CONFIG_PATH="${TEMPLATE_PATH}/cfg_complete.py"
LOCAL_CONFIG_PATH="${LOCAL_PATH}/config.py"
REMOTE_CONFIG_PATH="${REMOTE_PATH}/config.py"

LOCAL_MYCONFIG_PATH="${LOCAL_PATH}/myconfig.py"
REMOTE_MYCONFIG_PATH="${REMOTE_PATH}/myconfig.py"

TEMPLATE_MANAGE_PATH="${TEMPLATE_PATH}/complete.py"
REMOTE_MANAGE_PATH="${REMOTE_PATH}/manage.py"

LOCAL_MODELS_PATH="${LOCAL_PATH}/models"
REMOTE_MODELS_PATH="${REMOTE_PATH}/models"

echo "OVERWRITING LOCAL config.py WITH TEMPLATE"
cp "$TEMPLATE_CONFIG_PATH" "$LOCAL_CONFIG_PATH"

echo -e "\nSENDING config.py"
scp "$LOCAL_CONFIG_PATH" "$USER"@"$SRV":"$REMOTE_CONFIG_PATH"

if [[ -f "$LOCAL_MYCONFIG_PATH" ]]
then
    echo -e "\nSENDING myconfig.py"
    scp "$LOCAL_MYCONFIG_PATH" "$USER"@"$SRV":"$REMOTE_MYCONFIG_PATH"
else
    echo -e "\nRECEIVING myconfig.py"
    scp "$USER"@"$SRV":"$REMOTE_MYCONFIG_PATH" "$LOCAL_MYCONFIG_PATH"
fi

echo -e "\nSENDING TEMPLATE manage.py"
scp "$TEMPLATE_MANAGE_PATH" "$USER"@"$SRV":"$REMOTE_MANAGE_PATH"

echo -e "\nSENDING MODELS"
[[ ! -d "$LOCAL_MODELS_PATH" ]] && mkdir "$LOCAL_MODELS_PATH" # create local models dir if it does not exists
rsync -rv --progress --partial --delete --exclude=.DS_Store --exclude=.git "$LOCAL_MODELS_PATH" "$USER"@"$SRV":"$REMOTE_MODELS_PATH"

echo -e "\nRECEIVING DATA"
rsync -rv --progress --partial --include=data/*** --exclude=* "$USER"@"$SRV":"${REMOTE_PATH}/" "${LOCAL_PATH}/"
