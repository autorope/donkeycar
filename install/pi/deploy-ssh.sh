#!/bin/bash

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="."
fi
if [[ -e ${DCPATH}/files/bash_colors.sh ]]; then
    source ${DCPATH}/files/bash_colors.sh
fi

if [[ "$(whoami)" != "root" ]]; then
    echo "please run as root"
    exit 0
fi

mountpath="./dcdisk"
if [[ "${DCMOUNTPATH}" != "" ]]; then
    mountpath="${DCMOUNTPATH}"
fi

if [[ ! -e ${mountpath} ]]; then
    err "cannot deploy as mount path not found: ${mount_path}"
    exit 1
fi

ssh_id_rsa="${DCPATH}/files/id_rsa"
ssh_id_rsa_pub="${DCPATH}/files/id_rsa.pub"

if [[ ! -e ${ssh_id_rsa} ]]; then
    anmt "creating ssh keys for remote login using: pi@IP_FOR_THE_DONKEY_CAR"
    ssh-keygen -f ${DCPATH}/files/id_rsa -t rsa -N ''
fi

if [[ ! -e ${ssh_id_rsa} ]]; then
    err "failed creating ssh keys for the pi user"
    err "ssh-keygen -f ${DCPATH}/files/id_rsa -t rsa -N ''"
    exit 1
fi

anmt "installing keys:"
if [[ ! -e ${DCMOUNTPATH}/home/pi ]]; then
    err "failed to find pi home dir - please confirm the sd card is mounted:"
    err "$(ls -l ${DCMOUNTPATH})"
    exit 1
fi

if [[ ! -e ${DCMOUNTPATH}/home/pi/.ssh ]]; then
    mkdir -p -m 700 ${DCMOUNTPATH}/home/pi/.ssh
fi

if [[ ! -e ${DCMOUNTPATH}/root/.ssh ]]; then
    mkdir -p -m 700 ${DCMOUNTPATH}/root/.ssh
fi

cp ${ssh_id_rsa} ${DCMOUNTPATH}/home/pi/.ssh/id_rsa
cp ${ssh_id_rsa_pub} ${DCMOUNTPATH}/home/pi/.ssh/id_rsa.pub

if [[ -e "${HOME}/.ssh/id_rsa.pub" ]]; then
    anmt "installing ${HOME}/.ssh/id_rsa.pub as authorized user for: root and pi users"
    cat ${HOME}/.ssh/id_rsa.pub >> ${DCMOUNTPATH}/home/pi/.ssh/authorized_keys
    cat ${HOME}/.ssh/id_rsa.pub >> ${DCMOUNTPATH}/root/.ssh/authorized_keys
fi

if [[ -e "${DCPATH}/files/id_rsa.pub" ]]; then
    anmt "installing ${DCPATH}/files/id_rsa.pub as authorized user for: root and pi users"
    cat ${DCPATH}/files/id_rsa.pub >> ${DCMOUNTPATH}/home/pi/.ssh/authorized_keys
    cat ${DCPATH}/files/id_rsa.pub >> ${DCMOUNTPATH}/root/.ssh/authorized_keys
fi

chmod 600 ${DCMOUNTPATH}/home/pi/.ssh/authorized_keys
chmod 600 ${DCMOUNTPATH}/home/pi/.ssh/id_rsa
chmod 644 ${DCMOUNTPATH}/home/pi/.ssh/id_rsa.pub

cp ${DCMOUNTPATH}/home/pi/.ssh/authorized_keys ${DCMOUNTPATH}/root/.ssh/
cp ${DCMOUNTPATH}/home/pi/.ssh/id_rsa ${DCMOUNTPATH}/root/.ssh/
cp ${DCMOUNTPATH}/home/pi/.ssh/id_rsa.pub ${DCMOUNTPATH}/root/.ssh/

chmod 600 ${DCMOUNTPATH}/root/.ssh/authorized_keys
chmod 600 ${DCMOUNTPATH}/root/.ssh/id_rsa
chmod 644 ${DCMOUNTPATH}/root/.ssh/id_rsa.pub

chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/home/pi/.ssh
chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/home/pi/.ssh/authorized_keys
chown ${DCUSER}:${DCUSER} ${ssh_id_rsa} ${DCMOUNTPATH}/home/pi/.ssh/id_rsa
chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/home/pi/.ssh/id_rsa.pub

anmt "installing ssh config: ${DCMOUNTPATH}/etc/ssh/sshd_config"
cp ${DCMOUNTPATH}/etc/ssh/sshd_config ${DCMOUNTPATH}/etc/ssh/sshd_config.bak
cp ${DCPATH}/files/sshd_config ${DCMOUNTPATH}/etc/ssh/sshd_config

anmt "done installing ssh keys: ${ssh_id_rsa} and ${ssh_id_rsa_pub}"

# while mounted you can examine files as needed too:
# export DCDEBUG="1"
# or use the -d flag
if [[ "${DCDEBUG}" == "1" ]]; then
    inf ""
    anmt "pi user authorized keys file:"
    cat ${DCMOUNTPATH}/home/pi/.ssh/authorized_keys
    inf ""
fi

exit 0
