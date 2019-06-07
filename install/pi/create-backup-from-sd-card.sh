#!/bin/bash

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="."
fi
if [[ -e ${DCPATH}/files/bash_colors.sh ]]; then
    source ${DCPATH}/files/bash_colors.sh
fi
if [[ "$(whoami)" != "root" ]]; then
    exit 1
fi

# latest donkey car image id:
latest_version="donkey_2.6.1_pi3"
latest_image="${latest_version}.img"
latest_zip="${latest_version}.zip"
device="/dev/sdf"
if [[ "${DEVICE}" != "" ]]; then
    device="${DEVICE}"
fi
backup_dir="${DCPATH}/backups/img"
if [[ "${DCBACKUPDIR}" != "" ]]; then
    backup_dir="${DCBACKUPDIR}"
fi
zip_dir="${DCPATH}/backups/zip"
if [[ "${DCBACKUPDIR}" != "" ]]; then
    zip_dir="${DCBACKUPDIR}"
fi

if [[ ! -e ${backup_dir} ]]; then
    mkdir -p -m 777 ${backup_dir}
fi
if [[ ! -e ${zip_dir} ]]; then
    mkdir -p -m 777 ${zip_dir}
fi
backup_file="${backup_dir}/${latest_image}"
zip_file="${zip_dir}/${latest_zip}"
max_sectors=$(fdisk -l | grep "${device}2" | awk '{print $3}')
if [[ "${max_sectors}" == "" ]]; then
    err "unable to detect device with fdisk: fdisk -l | grep "${device}2" | awk '{print \$3}'"
    fdisk -l | grep "${device}"
    exit 1
fi

if [[ -e ${backup_file} ]] || [[ -e ${zip_file} ]]; then
    latest_version="donkey_2.6.1_pi3_$(date +'%Y_%m_%d_%H_%M_%S')"
    latest_image="${latest_version}.img"
    latest_zip="${latest_version}.zip"
    backup_file="${backup_dir}/${latest_image}"
    zip_file="${zip_dir}/${latest_zip}"
fi

anmt "creating ${device} backup max sectors ${max_sectors} to: ${backup_file}"
anmt "dd if=${device} of=${backup_file} bs=512 count=${max_sectors} status=progress"
dd if=${device} of=${backup_file} bs=512 count=${max_sectors} status=progress
if [[ "$?" != "0" ]]; then
    err "failed creating ${device} backup to: ${backup_file}"
    exit 1
fi

if [[ ! -e ${backup_file} ]]; then
    err "failed to find backup file for ${device} at: ${backup_file}"
    exit 1
fi
anmt "creating image zip: ${backup_file} as ${zip_file}"
zip ${zip_file} ${backup_file}

if [[ ! -e ${zip_file} ]]; then
    err "failed to find zip file for ${device} at: ${zip_file}"
    exit 1
fi

chmod 666 ${backup_file}
chmod 666 ${zip_file}

anmt "${latest_version} - backups completed"
anmt "image: ${backup_file}"
anmt "zip: ${zip_file}"

exit 0
