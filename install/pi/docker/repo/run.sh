#!/bin/bash

export DCREPO="https://github.com/jay-johnson/donkeycar.git"
export DCBRANCH="d1"
export DCPATH="/opt/dc"
export DCVENVDIR="/opt/venv"
export DCPYTHONVERSION="3.7"

if [[ ! -e /var/log/sdrepo.log ]]; then
    touch /var/log/sdrepo.log
    chmod 666 /var/log/sdrepo.log
fi
echo "" >> /var/log/sdrepo.log
echo "-----------------------" >> /var/log/sdrepo.log
echo "$(date +'%Y-%m-%d %H:%M:%S') - starting repo build - ${DCREPO} ${DCBRANCH} ${DCPATH} ${DCVENVDIR} ${DCPYTHONVERSION}" >> /var/log/sdrepo.log

if [[ -e /opt/dc/install/pi/files/rebuild_pip.sh ]]; then
    if [[ "$(whoami)" != "pi" ]]; then
        echo "local building as sudo -u pi user"
        sudo -u pi /bin/sh -c "/opt/dc/install/pi/files/rebuild_pip.sh >> /var/log/sdrepo.log 2>&1"
    else
        echo "local building as $(whoami) user"
        /opt/dc/install/pi/files/rebuild_pip.sh >> /var/log/sdrepo.log 2>&1
    fi
else
    echo "running remote github build tool"
    if [[ -e /tmp/rebuild_pip.sh ]]; then
        rm -f /tmp/rebuild_pip.sh
    fi
    not_done="1"
    num_attempts=0
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
fi

if [[ ! -e ${DCVENVDIR} ]]; then
    echo "failed to find python virtual env: ${DCVENVDIR} as $(whoami)"
    echo "virtualenv -p /usr/local/bin/python${DCPYTHONVERSION} ${DCVENVDIR}"
    exit 1
fi

if [[ ! -e ${DCPATH} ]]; then
    echo "failed to find repository: ${DCPATH} as $(whoami)"
    echo "git clone ${DCREPO} ${DCPATH}"
    exit 1
fi

echo "done installing ${DCREPO} at ${DCPATH} with branch ${DCBRANCH}"

exit 0
