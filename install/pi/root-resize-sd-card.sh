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

if [[ "${DEVICE}" != "/dev/sda" ]] && [[ "${DEVICE}" != "" ]]; then
    ./extend-sd-card.sh ${DEVICE} 2 apply
    if [[ "$?" != "0" ]]; then
        err "failed to extend ${DEVICE} storage"
        inf "./extend-sd-card.sh ${DEVICE} 2 apply"
        exit 1
    fi
fi

exit 0
