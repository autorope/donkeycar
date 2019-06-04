#!/bin/bash

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="/opt/dc/"
fi
if [[ -e ${DCPATH}/install/pi/files/bash_colors.sh ]]; then
    source ${DCPATH}/install/pi/files/bash_colors.sh
elif [[ -e ./install/pi/files/bash_colors.sh ]]; then
    source ./install/pi/files/bash_colors.sh
elif [[ -e ./files/bash_colors.sh ]]; then
    source ./files/bash_colors.sh
fi

ssh_id_rsa="${DCPATH}/install/pi/files/id_rsa"

if [[ ! -e ${ssh_id_rsa} ]]; then
    err "missing donkey car ssh keys for the pi user"
    err "ssh-keygen -f ${DCPATH}/files/id_rsa -t rsa -N ''"
    exit 1
fi

dc_address="${1}"
if [[ "${dc_address}" == "" ]]; then
    err "usage error: please pass the donkey car ip or fqdn to login like:"
    err "ssh -X -i ${ssh_id_rsa} pi@d1.example.com"
    exit 1
fi
anmt "logging into donkey car with:"
anmt "ssh -X -i ${ssh_id_rsa} pi@${dc_address}"
ssh -X -i ${ssh_id_rsa} pi@${dc_address}
good "logged out of donkey car: ${dc_address}"

exit 0
