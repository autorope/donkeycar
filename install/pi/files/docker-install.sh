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

anmt "adding docker apt repo"
if [[ ! -e /etc/apt/sources.list.d/docker.list ]]; then
    sudo touch /etc/apt/sources.list.d/docker.list
    sudo chmod 666 /etc/apt/sources.list.d/docker.list
fi

test_exists=$(cat /etc/apt/sources.list.d/docker.list | grep download.docker.com | grep raspbian | wc -l)
if [[ "${test_exists}" == "0" ]]; then
    echo "deb [arch=armhf] https://download.docker.com/linux/raspbian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
fi

anmt "checking docker repo file: /etc/apt/sources.list.d/docker.list"
cat /etc/apt/sources.list.d/docker.list

anmt "getting updates"
sudo apt-get update -y

anmt "reloading daemon"
sudo systemctl daemon-reload
anmt "enabling docker on reboot"
sudo systemctl enable docker.service

anmt "docker-install scheduling a reboot for the donkey car due to github issue: https://github.com/moby/moby/issues/21831"
sudo touch /opt/reboot-scheduled
sudo chmod 666 /opt/reboot-scheduled

exit 0
