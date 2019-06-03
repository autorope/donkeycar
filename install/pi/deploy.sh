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
    err "cannot deploy as mount path not found: ${mount_path}"
    exit 1
fi

anmt "starting deployment"

wifi_ssid="network_name"
wifi_password="password"

if [[ "${WIFINAME}" != "" ]]; then
    wifi_ssid="${WIFINAME}"
fi
if [[ "${WIFIPASSWORD}" != "" ]]; then
    wifi_password="${WIFIPASSWORD}"
fi

anmt "installing wifi credentials from environment vars: WIFINAME and WIFIPASSWORD to ${DCMOUNTPATH}/etc/wpa_supplicant/wpa_supplicant.conf"
cat <<EOF > ${DCMOUNTPATH}/etc/wpa_supplicant/wpa_supplicant.conf
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="${wifi_ssid}"
    psk="${wifi_password}"
}
EOF

# while mounted you can examine files as needed too:
# export DCDEBUG="1"
# or use the -d flag
if [[ "${DCDEBUG}" == "1" ]]; then
    inf ""
    anmt "wifi configuration file contents on the sd card:"
    cat ${DCMOUNTPATH}/etc/wpa_supplicant/wpa_supplicant.conf
    inf ""
fi

anmt "deploying ssh"
${DCPATH}/deploy-ssh.sh
if [[ "$?" != "0" ]]; then
    err "failed to deploy ssh to sd card:"
    inf "${DCPATH}/deploy-ssh.sh"
    exit 1
else
    good "deploy ssh - success"
fi

anmt "deploying tools"
${DCPATH}/deploy-tools.sh
if [[ "$?" != "0" ]]; then
    err "failed to deploy tools to sd card:"
    inf "${DCPATH}/deploy-tools.sh"
    exit 1
else
    good "deploy tools - success"
fi

exit 0
