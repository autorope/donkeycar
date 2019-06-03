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
    err "cannot unmount path because it was not found: ${mount_path}"
    exit 1
fi

if [[ "${DEVICE}" != "/dev/sda" ]] && [[ "${DEVICE}" != "" ]]; then
    umount ${DEVICE}2
    if [[ "$?" != "0" ]]; then
        err "failed to umount ${DEVICE}2"
        inf "umount ${DEVICE}2"
        exit 1
    fi
fi

exit 0
