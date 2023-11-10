#! /bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "${SCRIPT_DIR}/env.sh"

echo GIT RESET HARD DONKEYCAR REPO
ssh "$USER"@"$CAR_HOSTNAME" "cd ${REMOTE_DK_PATH} && git reset --hard"

echo -e "\nGIT PULL DONKEYCAR REPO"
ssh "$USER"@"$CAR_HOSTNAME" "cd ${REMOTE_DK_PATH} && git pull"

echo -e "\nCOPYING TEMPLATE manage.py"
scp "$USER"@"$CAR_HOSTNAME":"$TEMPLATE_MANAGE_PATH" "$USER"@"$CAR_HOSTNAME":"$REMOTE_MANAGE_PATH"
