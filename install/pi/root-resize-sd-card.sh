#!/bin/bash

# usage:
#
# export DEVICE=/dev/sdf
# optional env var:
# export DCGBTOADD=NUM_GB_TO_ADD
#   default NUM_GB_TO_ADD will increase the device's
#   2nd partition by 10 GB.
#   This extra space is hopefully enough to install
#   all the additional packages before creating a
#   new base image.
#
# Supported Command Line Parameters
# (note argument order is required for now)
#
# root-resize-sd-card.sh DEVICE NUM_GB_TO_ADD
#
# example: increase /dev/sdf's 2nd partition by 10 GB
# root-resize-sd-card.sh /dev/sdf 10
#

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

device_to_use="${1}"
# set by burn-image-to-sd-card.sh
if [[ "${DEVICE}" != "" ]]; then
    device_to_use="${DEVICE}"
fi
if [[ "${1}" != "" ]]; then
    device_to_use="${1}"
fi
gb_to_add=""
# set by burn-image-to-sd-card.sh
if [[ "${DCGBTOADD}" != "" ]]; then
    gb_to_add="${DCGBTOADD}"
fi
if [[ "${2}" != "" ]]; then
    gb_to_add="${2}"
fi

if [[ "${device_to_use}" != "/dev/sda" ]] && [[ "${device_to_use}" != "" ]]; then
    # add 10 GB more to the device partition
    last_status="0"
    if [[ "${gb_to_add}" == "" ]] || [[ "${gb_to_add}" == "max" ]] || [[ "${gb_to_add}" == "Max" ]]; then
        anmt "starting resize device: ${device_to_use} to max capacity"
        anmt "extending ${device_to_use} to max capacity with: ./extend-sd-card.sh ${device_to_use} 2 apply"
        ./extend-sd-card.sh ${device_to_use} 2 apply
        last_status="$?"
    else
        anmt "starting resize device: ${device_to_use} with requested additional GB capacity: ${gb_to_add}"
        anmt "extending ${device_to_use} with: ./extend-sd-card.sh ${device_to_use} 2 apply ${gb_to_add}"
        ./extend-sd-card.sh ${device_to_use} 2 apply ${gb_to_add}
        last_status="$?"
    fi
    if [[ "${last_status}" != "0" ]]; then
        err "failed to extend ${device_to_use} storage"
        inf "./extend-sd-card.sh ${device_to_use} 2 apply ${gb_to_add}"
        exit 1
    fi
fi

exit 0
