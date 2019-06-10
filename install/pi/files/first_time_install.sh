#!/bin/bash

export DCREPO="https://github.com/jay-johnson/donkeycar.git"
export DCBRANCH="d1"
export DCPATH="/opt/dc"
export DCVENVDIR="/opt/venv"
export DCPYTHONVERSION="3.7"

lg() {
    echo "$@"
}
inf() {
    lg "$@"
}
anmt() {
    lg "$@"
}
good() {
    lg "$@"
}
err() {
    lg "$@"
}
critical() {
    lg "$@"
}
warn() {
    lg "$@"
}
if [[ -e ${DCPATH}/install/pi/files/bash_colors.sh ]]; then
    source ${DCPATH}/install/pi/files/bash_colors.sh
fi

anmt "letting services start"
date +"%Y-%m-%d %H:%M:%S"
sleep 30

python_version="${DCPYTHONVERSION}"

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
fi

if [[ ! -e /usr/local/bin/python${python_version} ]] || [[ ! -e /usr/local/bin/pip${python_version} ]]; then
    err "failed to find installed python: ${python_version} /usr/local/bin/python${python_version} or pip: /usr/local/bin/pip${python_version}"
    echo ""
    echo "installed python versions:"
    ls -lrt /usr/local/bin/python*
    echo ""
    echo "installed pip versions:"
    ls -lrt /usr/local/bin/pip*
    exit 1
fi

if [[ ! -e /opt/dc ]]; then
    echo "running remote github build tool"
    if [[ -e /tmp/rebuild_pip.sh ]]; then
        rm -f /tmp/rebuild_pip.sh
    fi
    not_done="1"
    num_attempts=0
    if [[ -e /opt/allow_no_repo ]]; then
        not_done="0"
    fi
    if [[ "${not_done}" == "1" ]]; then
        if [[ -e /var/log/sdrepo.log ]]; then
            echo "" >> /var/log/sdrepo.log
            echo "" >> /var/log/sdrepo.log
            echo "--------------------------" >> /var/log/sdrepo.log
            echo "installing repo from GitHub Backup - $(date +"%Y-%m-%d %H:%M:%S")" >> /var/log/sdupdate.log
        fi
    fi
    while [[ "${not_done}" == "1" ]]; do
        if [[ ! -e /tmp/rebuild_pip.sh ]]; then
            curl https://raw.githubusercontent.com/jay-johnson/donkeycar/d1/install/pi/files/rebuild_pip.sh -o /tmp/rebuild_pip.sh
        fi
        if [[ -e /tmp/rebuild_pip.sh ]]; then
            if [[ -e /tmp/rebuild_pip.sh ]]; then
                chmod 777 /tmp/rebuild_pip.sh
                if [[ "$(whoami)" != "pi" ]]; then
                    echo "curl - rebuilding as sudo -u pi user"
                    sudo -u pi /bin/sh -c "/tmp/rebuild_pip.sh >> /var/log/sdrepo.log 2>&1"
                else
                    echo "curl - rebuilding as $(whoami) user"
                    /tmp/rebuild_pip.sh >> /var/log/sdrepo.log 2>&1
                fi

                if [[ -e ${DCVENVDIR} ]] && [[ -e ${DCPATH} ]]; then
                    echo "curl - repo ${DCREPO} cloned at: ${DCPATH} with virtual env: ${DCVENVDIR}"
                    not_done="0"
                fi
            fi
        fi
        if [[ "${not_done}" == "1" ]]; then
            num_attempts=$((num_attempts++))
            if [[ ${num_attempts} -gt 180 ]]; then
                echo "stopping retry attempts to rebuild the repository after 180 attempts"
                not_done="0"
            else
                echo "retrying to rebuild the repository in 10 seconds - ${num_attempts}/180 - $(date +'%Y-%m-%d %H:%M:%S')"
                sleep 10
            fi
        fi
    done
    if [[ -e /tmp/rebuild_pip.sh ]]; then
        rm -f /tmp/rebuild_pip.sh
    fi
else
    if [[ -e /var/log/sdrepo.log ]]; then
        echo "" >> /var/log/sdrepo.log
        echo "" >> /var/log/sdrepo.log
        echo "--------------------------" >> /var/log/sdrepo.log
        echo "installing repo /opt/dc/install/pi/docker/repo/run.sh - $(date +"%Y-%m-%d %H:%M:%S")" >> /var/log/sdupdate.log
    fi
    anmt "installing repo" >> /var/log/sdrepo.log 2>&1
    echo "sudo -u pi /bin/sh -c \"/opt/dc/install/pi/docker/repo/run.sh >> /var/log/sdrepo.log 2>&1\""
    sudo -u pi /bin/sh -c "/opt/dc/install/pi/docker/repo/run.sh >> /var/log/sdrepo.log 2>&1"
    if [[ "$?" != "0" ]]; then
        err "failed to install repo on the donkey car os: /opt/dc/install/pi/docker/repo/run.sh" >> /var/log/sdrepo.log 2>&1
        exit 1
    fi
    good "done - installing repo" >> /var/log/sdrepo.log 2>&1
fi

if [[ ! -e /opt/dc ]]; then
    err "failed to clone repository to /opt/dc"
    exit 1
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
