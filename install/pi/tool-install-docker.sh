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
    err "cannot install docker tool as mount path not found: ${mount_path}"
    exit 1
fi

cp ${DCPATH}/files/docker-install.sh ${DCMOUNTPATH}/etc/cron.daily/
cp ${DCPATH}/files/hourly_cron ${DCMOUNTPATH}/etc/cron.hourly/

custom_rc_local=${DCPATH}/files/rc.local
if [[ "${DCSTARTUP}" != "" ]]; then
    custom_rc_local="${DCSTARTUP}"
    anmt "using custom DCSTARTUP=${DCSTARTUP}"
fi

if [[ -e ${custom_rc_local} ]]; then
    anmt "installing rc.local ${custom_rc_local} to ${DCMOUNTPATH}/etc/rc.local"
    cp ${custom_rc_local} ${DCMOUNTPATH}/etc/rc.local
fi

anmt "done installing tools"

# while mounted you can examine files as needed too:
# export DCDEBUG="1"
# or use the -d flag
if [[ "${DCDEBUG}" == "1" ]]; then
    inf ""
    anmt "daily cron:"
    cat ${DCMOUNTPATH}/etc/cron.daily/daily_cron
    anmt "hourly cron:"
    cat ${DCMOUNTPATH}/etc/cron.daily/hourly_cron
    inf ""
fi

exit 0
