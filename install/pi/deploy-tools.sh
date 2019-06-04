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
dcrepo="https://github.com/autorope/donkeycar.git"
if [[ "${DCREPO}" != "" ]]; then
    dcrepo="${DCREPO}"
fi
dcbranch="dev"
if [[ "${DCBRANCH}" != "" ]]; then
    dcbranch="${DCBRANCH}"
fi
splunk_user="pi"
if [[ "${DCSPLUNKUSER}" != "" ]]; then
    splunk_user="${DCSPLUNKUSER}"
fi
splunk_password="123321"
if [[ "${DCSPLUNKPASSWORD}" != "" ]]; then
    splunk_password="${DCSPLUNKPASSWORD}"
fi
splunk_host="logs.example.com"
if [[ "${DCSPLUNKHOST}" != "" ]]; then
    splunk_host="${DCSPLUNKHOST}"
fi
# default packages to install
initial_packages_to_install="apt-transport-https ca-certificates curl git libffi-dev libssl-dev netcat net-tools software-properties-common vim"
if [[ "${DCINSTALLPACKAGES}" != "" ]]; then
    initial_packages_to_install="${DCINSTALLPACKAGES}"
fi

if [[ ! -e ${mountpath} ]]; then
    err "cannot deploy as mount path not found: ${mount_path}"
    exit 1
fi

cp ${DCPATH}/files/daily_cron ${DCMOUNTPATH}/etc/cron.daily/
cp ${DCPATH}/files/hourly_cron ${DCMOUNTPATH}/etc/cron.hourly/

if [[ -e ${DCMOUNTPATH}/home/pi/.bashrc ]]; then
    cp ${DCMOUNTPATH}/home/pi/.bashrc ${DCMOUNTPATH}/home/pi/.bashrc_bak
fi
if [[ -e ${DCMOUNTPATH}/home/pi/.vimrc ]]; then
    cp ${DCMOUNTPATH}/home/pi/.vimrc ${DCMOUNTPATH}/home/pi/.vimrc_bak
fi
if [[ -e ${DCMOUNTPATH}/home/pi/.gitconfig ]]; then
    cp ${DCMOUNTPATH}/home/pi/.gitconfig ${DCMOUNTPATH}/home/pi/.gitconfig_Bak
fi

cp ${DCPATH}/files/bashrc ${DCMOUNTPATH}/home/pi/.bashrc
cp ${DCPATH}/files/vimrc ${DCMOUNTPATH}/home/pi/.vimrc
cp ${DCPATH}/files/gitconfig ${DCMOUNTPATH}/home/pi/.gitconfig

chmod 644 ${DCMOUNTPATH}/home/pi/.bashrc
chmod 644 ${DCMOUNTPATH}/home/pi/.vimrc
chmod 644 ${DCMOUNTPATH}/home/pi/.gitconfig

chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/home/pi/.bashrc
chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/home/pi/.vimrc
chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/home/pi/.gitconfig

cp ${DCPATH}/files/bashrc ${DCMOUNTPATH}/root/.bashrc
cp ${DCPATH}/files/vimrc ${DCMOUNTPATH}/root/.vimrc
cp ${DCPATH}/files/gitconfig ${DCMOUNTPATH}/root/.gitconfig

custom_rc_local=${DCPATH}/files/rc.local
if [[ "${DCSTARTUP}" != "" ]]; then
    custom_rc_local="${DCSTARTUP}"
    anmt "using custom DCSTARTUP=${DCSTARTUP}"
fi

if [[ -e ${custom_rc_local} ]]; then
    anmt "installing rc.local ${custom_rc_local} to ${DCMOUNTPATH}/etc/rc.local"
    cp ${custom_rc_local} ${DCMOUNTPATH}/etc/rc.local
fi

if [[ ! -e "${DCMOUNTPATH}/opt/dc" ]]; then
    anmt "cloning donkey car repo ${dcrepo} on ${dcbranch} branch to: ${DCMOUNTPATH}/opt/dc"
    git clone ${dcrepo} ${DCMOUNTPATH}/opt/dc
    if [[ ! -e "${DCMOUNTPATH}/opt/dc" ]]; then
        err "failed to clone repo: ${dcrepo}"
        err "git clone ${dcrepo} ${DCMOUNTPATH}/opt/dc"
        exit 1
    fi
    pushd ${DCMOUNTPATH}/opt/dc >> /dev/null
    git checkout ${dcbranch}
    popd >> /dev/null
else
    pushd ${DCMOUNTPATH}/opt/dc >> /dev/null
    echo ""
    anmt "fetching $(pwd):"
    git fetch
    anmt "checking out ${dcbranch} $(pwd):"
    git checkout ${dcbranch}
    anmt "pulling updates $(pwd):"
    git pull
    echo ""
    anmt "repo status $(pwd):"
    git status
    echo ""
    anmt "repo last commit $(pwd):"
    git log -1
    popd >> /dev/null
fi

if [[ -e "${DCMOUNTPATH}/opt/dc" ]]; then
    anmt "setting chown for ${DCUSER}:${DCUSER} on: ${DCMOUNTPATH}/opt/dc"
    chown -R ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/opt/dc
fi

anmt "setting /opt as useable"
chmod 777 ${DCMOUNTPATH}/opt

custom_docker_daemon=${DCPATH}/files/docker-daemon.json
if [[ "${DCDOCKERDAEMON}" != "" ]]; then
    custom_docker_daemon="${DCDOCKERDAEMON}"
    anmt "using custom DCDOCKERDAEMON=${DCDOCKERDAEMON}"
fi

if [[ ! -e ${DCMOUNTPATH}/etc/docker ]]; then
    mkdir -p -m 755 ${DCMOUNTPATH}/etc/docker
fi

if [[ -e "${custom_docker_daemon}" ]]; then
    anmt "installing docker daemon.json from ${custom_docker_daemon} to /etc/docker/daemon.json"
    cp ${custom_docker_daemon} ${DCMOUNTPATH}/etc/docker/daemon.json
fi

if [[ "${DCDOCKERUSER}" != "" ]] && [[ "${DCDOCKERPASSWORD}" != "" ]] && [[ "${DCDOCKERREGISTRY}" != "" ]]; then
    sed -i "s/REPLACE_DOCKER_ENABLED/1/g" ${DCMOUNTPATH}/home/pi/.bashrc
    sed -i "s/REPLACE_DC_DOCKER_USER/${DCDOCKERUSER}/g" ${DCMOUNTPATH}/home/pi/.bashrc
    sed -i "s/REPLACE_DC_DOCKER_PASSWORD/${DCDOCKERPASSWORD}/g" ${DCMOUNTPATH}/home/pi/.bashrc
    sed -i "s/REPLACE_DC_DOCKER_REGISTRY/${DCDOCKERREGISTRY}/g" ${DCMOUNTPATH}/home/pi/.bashrc

    cp ${DCPATH}/files/login_to_docker.sh ${DCMOUNTPATH}/opt/login_to_docker.sh
    chmod 777 ${DCMOUNTPATH}/opt/login_to_docker.sh

    sed -i "s/REPLACE_DOCKER_ENABLED/1/g" ${DCMOUNTPATH}/opt/login_to_docker.sh
    sed -i "s/REPLACE_DC_DOCKER_USER/${DCDOCKERUSER}/g" ${DCMOUNTPATH}/opt/login_to_docker.sh
    sed -i "s/REPLACE_DC_DOCKER_PASSWORD/${DCDOCKERPASSWORD}/g" ${DCMOUNTPATH}/opt/login_to_docker.sh
    sed -i "s/REPLACE_DC_DOCKER_REGISTRY/${DCDOCKERREGISTRY}/g" ${DCMOUNTPATH}/opt/login_to_docker.sh
fi

anmt "installing initial package installer for first time-boot installs: /opt/first_time_install.sh"
anmt "cp ${DCPATH}/files/first_time_install.sh ${DCMOUNTPATH}/opt/first_time_install.sh"
cp ${DCPATH}/files/first_time_install.sh ${DCMOUNTPATH}/opt/first_time_install.sh
chmod 777 ${DCMOUNTPATH}/opt/first_time_install.sh

echo "created on $(date +"%Y-%m-%d %H:%M:%S")" > ${DCMOUNTPATH}/var/log/sdinstall.log
echo "created on $(date +"%Y-%m-%d %H:%M:%S")" > ${DCMOUNTPATH}/var/log/sdrepo.log
echo "created on $(date +"%Y-%m-%d %H:%M:%S")" > ${DCMOUNTPATH}/var/log/sdupdate.log
chmod 666 ${DCMOUNTPATH}/var/log/sdinstall.log
chmod 666 ${DCMOUNTPATH}/var/log/sdrepo.log
chmod 666 ${DCMOUNTPATH}/var/log/sdupdate.log

splunk_token="NOTFOUND"
test_splunk=$(docker ps | grep splunk | wc -l)
if [[ "${test_splunk}" == "1" ]]; then
    anmt "getting splunk token from splunk container"
    splunk_token=$(docker exec -it splunk /bin/bash -c "ps auwwx ; /opt/splunk/bin/splunk http-event-collector list -uri "https://${splunk_user}:${splunk_password}@localhost:8089"" | grep 'token='  | sed -e 's/=/ /g' | awk '{print $NF}' | sed "s/\n//g" | sed "s/\r//g" | head -1)
    anmt "installing splunk token: ${DCMOUNTPATH}/opt/fluent-bit-includes/config-fluent-bit-in-tcp-out-splunk.yaml"
    if [[ ! -e ${DCMOUNTPATH}/opt/fluent-bit-includes ]]; then
        mkdir -p -m 777 ${DCMOUNTPATH}/opt/fluent-bit-includes
    fi
    if [[ ! -e ${DCMOUNTPATH}/opt/fluent-bit-includes/config-fluent-bit-in-tcp-out-splunk.yaml ]]; then
        cp ${DCPATH}/files/config-fluent-bit-in-*.yaml ${DCMOUNTPATH}/opt/fluent-bit-includes/
        chmod 775 ${DCMOUNTPATH}/opt/fluent-bit-includes/*
        chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/opt/fluent-bit-includes/*
    fi
    sed -i "s|REPLACE_SPLUNK_TOKEN|${splunk_token}|g" ${DCMOUNTPATH}/opt/fluent-bit-includes/config-fluent-bit-in-tcp-out-splunk.yaml
    if [[ "$?" != "0" ]]; then
        err "failed to install splunk token: ${splunk_token} into file: ${DCMOUNTPATH}/opt/fluent-bit-includes/config-fluent-bit-in-tcp-out-splunk.yaml"
        echo "sed -i \"s|REPLACE_SPLUNK_TOKEN|${splunk_token}|g\" ${DCMOUNTPATH}/opt/fluent-bit-includes/config-fluent-bit-in-tcp-out-splunk.yaml"
    fi
    sed -i "s|REPLACE_SPLUNK_HOST|${splunk_host}|g" ${DCMOUNTPATH}/opt/fluent-bit-includes/config-fluent-bit-in-tcp-out-splunk.yaml
    if [[ "$?" != "0" ]]; then
        err "failed to install splunk HEC host: ${splunk_host} into file: ${DCMOUNTPATH}/opt/fluent-bit-includes/config-fluent-bit-in-tcp-out-splunk.yaml"
    fi
fi

# trigger first time installs of packages and upgrades
echo "${initial_packages_to_install}" > ${DCMOUNTPATH}/opt/install-packages
chmod 666 ${DCMOUNTPATH}/opt/install-packages
chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/opt/install-packages
touch ${DCMOUNTPATH}/opt/upgrade-packages
chmod 666 ${DCMOUNTPATH}/opt/upgrade-packages
chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/opt/upgrade-packages

if [[ ! -e ${DCMOUNTPATH}/opt/downloads ]]; then
    mkdir -p -m 777 ${DCMOUNTPATH}/opt/downloads
    chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/opt/downloads
fi

if [[ ! -e ${DCMOUNTPATH}/opt/downloads/pip ]]; then
    mkdir -p -m 777 ${DCMOUNTPATH}/opt/downloads/pip
    chown ${DCUSER}:${DCUSER} ${DCMOUNTPATH}/opt/downloads/pip
fi

scipy_version="scipy-1.2.1-cp35-cp35m-linux_armv7l.whl"
scipy_url="https://www.piwheels.org/simple/scipy/${scipy_version}#sha256=270be300233af556e6ee3f55a0ae237df0cb65ac85d47559010d7a9071f2e878"
scipy_download_file="${DCMOUNTPATH}/opt/downloads/pip/${scipy_version}"

if [[ ! -e ${scipy_download_file} ]]; then
    anmt "downloading newer scipy wheel file for install on the donkey car first time boot"
    wget ${scipy_url} -O ${scipy_download_file}
    chmod 666 ${scipy_download_file}
    chown ${DCUSER}:${DCUSER} ${scipy_download_file}
fi

if [[ ! -e ${scipy_download_file} ]]; then
    err "failed to download ${scipy_version} from url: ${scipy_url}"
    echo "wget ${scipy_url} -O ${scipy_download_file}"
else
    anmt "scipy ready for install on device at path: /opt/downloads/pip/${scipy_version}"
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
