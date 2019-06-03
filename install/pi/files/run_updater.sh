#!/bin/bash

test_exists=$(which docker | wc -l)
if [[ "${test_exists}" != "0" ]]; then
    echo "docker is already installed"
    exit 0
fi

export DCPATH=/opt/dc
if [[ -e ${DCPATH}/install/pi/files/bash_colors.sh ]]; then
    source ${DCPATH}/install/pi/files/bash_colors.sh
fi

anmt "getting updates"
date +"%Y-%m-%d %H:%M:%S"

apt-get update -y

anmt "updating packages"
date +"%Y-%m-%d %H:%M:%S"

apt-get install -y \ 
    apt-transport-https \
    ca-certificates \
    git \
    net-tools \
    software-properties-common \
    vim

date +"%Y-%m-%d %H:%M:%S"
good "done"

EXITVALUE=0
exit $EXITVALUE
