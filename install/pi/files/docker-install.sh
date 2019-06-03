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

anmt "Installing Docker"
date +"%Y-%m-%d %H:%M:%S"

# instructions from:
# https://blog.docker.com/2019/03/happy-pi-day-docker-raspberry-pi/

anmt "installing initial packages"
apt-get install apt-transport-https ca-certificates software-properties-common -y

anmt "installing with get-docker.sh"
curl -fsSL get.docker.com -o get-docker.sh && sh get-docker.sh

anmt "adding pi user to docker group"
usermod -aG docker pi

curl https://download.docker.com/linux/raspbian/gpg

test_exists=$(cat /etc/apt/sources.list | grep download.docker.com | wc -l)
if [[ "${test_exists}" == "0" ]]; then
    echo "deb https://download.docker.com/linux/raspbian/ stretch stable" >> /etc/apt/sources.list
fi

anmt "getting updates"
apt-get update -y
anmt "starting upgrade"
apt-get upgrade -y

anmt "reloading daemon"
systemctl daemon-reload
anmt "enabling docker on reboot"
systemctl enable docker.service
anmt "starting docker"
systemctl start docker.service

EXITVALUE=0
if [[ "REPLACE_DOCKER_ENABLED" == "1" ]]; then
    if [[ -e /opt/login_to_docker.sh ]]; then
        anmt "sleeping before trying to login to the docker registry"
        date +"%Y-%m-%d %H:%M:%S"
        sleep 60
        anmt "done sleeping - trying to login to the registry"
        date +"%Y-%m-%d %H:%M:%S"
        /opt/login_to_docker.sh
        EXITVALUE=$?
    fi
fi

exit $EXITVALUE
