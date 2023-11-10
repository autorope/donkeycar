#! /bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "${SCRIPT_DIR}/env.sh"

TEMPLATE_CONFIG_PATH="${LOCAL_DK_PATH}/donkeycar/templates/cfg_complete.py"
LOCAL_CONFIG_PATH="${LOCAL_CAR_PATH}/config.py"
REMOTE_CONFIG_PATH="${REMOTE_CAR_PATH}/config.py"

LOCAL_MYCONFIG_PATH="${LOCAL_CAR_PATH}/myconfig.py"
REMOTE_MYCONFIG_PATH="${REMOTE_CAR_PATH}/myconfig.py"

LOCAL_MODELS_PATH="${LOCAL_CAR_PATH}/models/"
REMOTE_MODELS_PATH="${REMOTE_CAR_PATH}/models/"

echo "OVERWRITING LOCAL config.py WITH TEMPLATE"
cp "$TEMPLATE_CONFIG_PATH" "$LOCAL_CONFIG_PATH"

echo -e "\nSENDING config.py"
scp "$LOCAL_CONFIG_PATH" "$USER"@"$CAR_HOSTNAME":"$REMOTE_CONFIG_PATH"

if [[ -f "$LOCAL_MYCONFIG_PATH" ]]
then
    echo -e "\nSENDING myconfig.py"
    scp "$LOCAL_MYCONFIG_PATH" "$USER"@"$CAR_HOSTNAME":"$REMOTE_MYCONFIG_PATH"
else
    echo -e "\nRECEIVING myconfig.py"
    scp "$USER"@"$CAR_HOSTNAME":"$REMOTE_MYCONFIG_PATH" "$LOCAL_MYCONFIG_PATH"
fi

echo -e "\nSENDING MODELS"
[[ ! -d "$LOCAL_MODELS_PATH" ]] && mkdir "$LOCAL_MODELS_PATH" # create local models dir if it does not exists
rsync -rv --progress --partial --delete --exclude=.DS_Store --exclude=.git "$LOCAL_MODELS_PATH" "$USER"@"$CAR_HOSTNAME":"$REMOTE_MODELS_PATH"

echo -e "\nRECEIVING DATA"
rsync -rv --progress --partial --include=data/*** --exclude=* "$USER"@"$CAR_HOSTNAME":"${REMOTE_CAR_PATH}/" "${LOCAL_CAR_PATH}/"
