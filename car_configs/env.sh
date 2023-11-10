USER=donkey
CAR_HOSTNAME_SUFFIX=".local" # "" or ".local"
CAR_NAME=$(basename $(pwd))
CAR_HOSTNAME="${CAR_NAME}${CAR_HOSTNAME_SUFFIX}"

REMOTE_CAR_HOME="/home/${USER}"
REMOTE_CAR_PATH="${REMOTE_CAR_HOME}/car"
REMOTE_DK_PATH="${REMOTE_CAR_HOME}/donkeycar"

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LOCAL_CAR_PATH="${SCRIPT_PATH}/${CAR_NAME}"
LOCAL_DK_PATH=$( cd -- "${SCRIPT_PATH}/.." && pwd )

TEMPLATE_MANAGE_PATH="${REMOTE_DK_PATH}/donkeycar/templates/complete.py"
REMOTE_MANAGE_PATH="${REMOTE_CAR_PATH}/manage.py"

EXEC_PATH=$( cd -- "$(pwd)/.." && pwd )

if [[ ! $(basename "$EXEC_PATH") == "car_configs" ]]
then
    echo "This script MUST be run within a subdirectory of car_configs directory."
    exit -1
fi
