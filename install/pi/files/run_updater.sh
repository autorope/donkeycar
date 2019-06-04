#!/bin/bash

export DCPATH=/opt/dc
if [[ -e ${DCPATH}/install/pi/files/bash_colors.sh ]]; then
    source ${DCPATH}/install/pi/files/bash_colors.sh
fi

anmt "starting upgrade"
date +"%Y-%m-%d %H:%M:%S"

# from blog: https://raymii.org/s/blog/Raspberry_Pi_Raspbian_Unattended_Upgrade_Jessie_to_Testing.html
sudo DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" dist-upgrade
if [[ "$?" != "0" ]]; then
    err "failed to upgrade before installing initial packages"
    exit 1
else
    # Remove no longer needed packages
    anmt "removing stale packages now that the upgrade is done"
    sudo DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" autoremove --purge
    date +"%Y-%m-%d %H:%M:%S"
    good "upgrade packages - complete"
fi

date +"%Y-%m-%d %H:%M:%S"
good "done"

EXITVALUE=0
exit $EXITVALUE
