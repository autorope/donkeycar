#!/bin/bash

export DCPATH=/opt/dc
if [[ -e ${DCPATH}/install/pi/files/bash_colors.sh ]]; then
    source ${DCPATH}/install/pi/files/bash_colors.sh
fi

anmt "letting services start"
date +"%Y-%m-%d %H:%M:%S"
sleep 30

python_version="3.7"

anmt "getting updates"
date +"%Y-%m-%d %H:%M:%S"
sudo apt-get update -y \
    -o "Dpkg::Options::=--force-confdef" \
    -o "Dpkg::Options::=--force-confold" >> /var/log/sdupdate.log 2>&1

if [[ -e /opt/upgrade-packages ]]; then
    anmt "starting upgrade"
    date +"%Y-%m-%d %H:%M:%S"
    # from blog: https://raymii.org/s/blog/Raspberry_Pi_Raspbian_Unattended_Upgrade_Jessie_to_Testing.html
    sudo DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" dist-upgrade >> /var/log/sdupdate.log 2>&1
    if [[ "$?" != "0" ]]; then
        err "failed to upgrade before installing initial packages"
        exit 1
    else
        # Remove no longer needed packages
        anmt "removing stale packages now that the upgrade is done"
        sudo DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" autoremove --purge >> /var/log/sdupdate.log 2>&1
        date +"%Y-%m-%d %H:%M:%S"
        good "upgrade packages - complete"
    fi
    sudo rm -f /opt/upgrade-packages
else
    anmt "no package upgrade scheduled: /opt/upgrade-packages"
fi

if [[ -e /opt/install-packages ]]; then
    anmt "detected install packages request"
    install_packages=$(sudo cat /opt/install-packages)
    anmt "installing packages: ${install_packages}"
    date +"%Y-%m-%d %H:%M:%S"
    sudo apt-get install -y \
        -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" \
        ${install_packages} >> /var/log/sdinstall.log 2>&1

    if [[ "$?" != "0" ]]; then
        err "failed to initial packages: ${install_packages}"
        exit 1
    else
        date +"%Y-%m-%d %H:%M:%S"
        good "install initial packages - complete"
    fi

    if [[ ! -e /opt/no-build-packages ]]; then
        if [[ -e /opt/dc/install/pi/docker/base/run.sh ]]; then
            anmt "starting install of build packages"
            anmt "sudo /opt/dc/install/pi/docker/base/run.sh"
            date +"%Y-%m-%d %H:%M:%S"
            sudo /opt/dc/install/pi/docker/base/run.sh
            if [[ "$?" != "0" ]]; then
                err "failed to install build packages for the donkey car os: /opt/dc/install/pi/docker/base/run.sh"
                exit 1
            fi
            date +"%Y-%m-%d %H:%M:%S"
            good "starting install of build packages - complete"
        fi
    fi

    sudo rm -f /opt/install-packages
else
    anmt "no package install scheduled: /opt/install-packages"
fi

if [[ ! -e /opt/stay-on-python35 ]] && [[ ! -e /usr/local/bin/python${python_version} ]] && [[ ! -e /usr/local/bin/pip${python_version} ]]; then
    anmt "installing python ${python_version}.3" >> /var/log/sdinstall.log 2>&1
    sudo /opt/dc/install/pi/docker/python${python_version}/run.sh >> /var/log/sdinstall.log 2>&1
    if [[ "$?" != "0" ]]; then
        err "failed to install python ${python_version} for the donkey car os: /opt/dc/install/pi/docker/python${python_version}/run.sh" >> /var/log/sdinstall.log 2>&1
        exit 1
    fi
    good "done - installing python ${python_version}.3" >> /var/log/sdinstall.log 2>&1

    anmt "installing repo" >> /var/log/sdinstall.log 2>&1
    sudo /opt/dc/install/pi/docker/repo/run.sh >> /var/log/sdinstall.log 2>&1
    if [[ "$?" != "0" ]]; then
        err "failed to install repo on the donkey car os: /opt/dc/install/pi/docker/repo/run.sh" >> /var/log/sdinstall.log 2>&1
        exit 1
    fi
    good "done - installing repo" >> /var/log/sdinstall.log 2>&1
fi

if [[ -e ${DCPATH}/install/pi/files/rebuild_pip.sh ]]; then
    anmt "rebuilding pip in ${DCPATH} with: ${DCPATH}/install/pi/files/rebuild_pip.sh"
    chmod 777 ${DCPATH}/install/pi/files/rebuild_pip.sh
    ${DCPATH}/install/pi/files/rebuild_pip.sh >> /var/log/sdrepo.log 2>&1
fi

# https://docs.fluentbit.io/manual/getting_started
if [[ -e ${DCPATH}/install/pi/files/fluent-bit-install.sh ]]; then
    anmt "installing fluent bit with: ${DCPATH}/install/pi/files/fluent-bit-install.sh"
    chmod 777 ${DCPATH}/install/pi/files/fluent-bit-install.sh
    ${DCPATH}/install/pi/files/fluent-bit-install.sh >> /var/log/sdinstall.log 2>&1
fi

# for now, docker requires a reboot to work after installing:

test_exists=$(which docker | wc -l)
if [[ "${test_exists}" == "0" ]]; then
    if [[ -e ${DCPATH}/install/pi/files/docker-install.sh ]]; then
        anmt "installing docker: ${DCPATH}/install/pi/files/docker-install.sh"
        chmod 777 ${DCPATH}/install/pi/files/docker-install.sh
        ${DCPATH}/install/pi/files/docker-install.sh >> /var/log/sdinstall.log 2>&1
    fi
fi

date +"%Y-%m-%d %H:%M:%S"
good "done"

EXITVALUE=0
exit $EXITVALUE
