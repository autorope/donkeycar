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

if [[ "${DEVICE}" == "" ]]; then
    if [[ "${1}" != "" ]]; then
        DEVICE="${1}"
    fi
fi

if [[ "${DEVICE}" != "/dev/sda" ]] && [[ "${DEVICE}" != "" ]] && [[ -e "${DEVICE}" ]]; then
    anmt "sleeping for 5 seconds before deleting anything on the ${DEVICE} partitions in case you need to save"
    sleep 1
    anmt "sleeping for 4 seconds before deleting anything on the ${DEVICE} partitions in case you need to save"
    sleep 1
    anmt "sleeping for 3 seconds before deleting anything on the ${DEVICE} partitions in case you need to save"
    sleep 1
    anmt "sleeping for 2 seconds before deleting anything on the ${DEVICE} partitions in case you need to save"
    sleep 1
    anmt "sleeping for 1 seconds before deleting anything on the ${DEVICE} partitions in case you need to save"
    sleep 1

    good "deleting ${DEVICE} partition 1"
    parted -s ${DEVICE} rm 1 > /dev/null 2>&1
    good "deleting ${DEVICE} partition 2"
    parted -s ${DEVICE} rm 2 > /dev/null 2>&1
else
    err "missing a valid device: ${DEVICE}"
    exit 1
fi

exit 0
