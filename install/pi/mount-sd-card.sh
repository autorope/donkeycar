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
    mkdir -p ${mountpath}
    chmod 775 ${mountpath}
fi

if [[ ! -e ${mountpath} ]]; then
    err "failed to build mount path: ${mountpath}"
    exit 1
fi

if [[ "${DEVICE}" != "/dev/sda" ]] && [[ "${DEVICE}" != "" ]]; then
    mount ${DEVICE}2 ${mountpath}
    if [[ "$?" != "0" ]]; then
        err "failed to mount ${DEVICE}2 to ${mountpath}"
        inf "mount ${DEVICE}2 ${mountpath}"
        exit 1
    fi
fi

exit 0
