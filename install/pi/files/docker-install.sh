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

anmt "installing docker gpg key"
sudo curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -

anmt "curling get.docker.com -o get-docker.sh"
sudo curl -fsSL get.docker.com -o get-docker.sh
anmt "installing with get-docker.sh"
sudo sh get-docker.sh

anmt "adding pi user to docker group"
sudo usermod -aG docker pi

anmt "adding docker apt-registry"
sudo add-apt-repository \
   "deb [arch=armhf] https://download.docker.com/linux/debian \
   $(lsb_release -cs) \
   stable"

anmt "getting updates"
sudo apt-get update -y

anmt "reloading daemon"
sudo systemctl daemon-reload
anmt "enabling docker on reboot"
sudo systemctl enable docker.service
anmt "starting docker"
sudo systemctl start docker.service
# this can hang automation:
# anmt "checking docker status"
# sudo systemctl status docker.service

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
