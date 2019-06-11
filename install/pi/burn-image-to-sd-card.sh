#!/bin/bash

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="."
fi
if [[ -e ${DCPATH}/files/bash_colors.sh ]]; then
    source ${DCPATH}/files/bash_colors.sh
fi

if [[ "$(whoami)" != "root" ]]; then
    err "please run as root"
    exit 1
fi

# Default to the sd card reader
if [[ "${DEVICE}" == "" ]]; then
    found_default=$(parted print -l | grep sdf | wc -l)
    if [[ "${found_default}" == "0" ]]; then
        err "please set your sd reader card path as an environment variable:"
        err "# export DEVICE=/dev/sdf"
        err "export DEVICE=SD_READER_DEVICE_PATH"
        exit 1
    else
        export DEVICE=/dev/sdf
    fi
fi

# install this repo:
dcrepo="https://github.com/jay-johnson/donkeycar.git"
# install this branch:
dcbranch="d1"

# original donkey car dev branch 2.5.0 with python 3.5 build:
# https://drive.google.com/file/d/1vr4nEXLEh4xByKAXik8KhK3o-XWgo2fQ/view
fileid="1vr4nEXLEh4xByKAXik8KhK3o-XWgo2fQ" # contains zip file: donkey_2.5.0_pi3.zip
#
# or you can use custom images by the google file id from the url:
#
# donkey car jay-johnson@d1 branch with python 3.7 build:
# https://drive.google.com/file/d/1OBcPjdZG-vug5Qyq2tYF6zjtVBQffbsQ/view
# fileid="1OBcPjdZG-vug5Qyq2tYF6zjtVBQffbsQ" # contains zip file: donkey_python37_from_d1_branch.zip
# or you can pass this file id as an arg:
# ./burn-image-to-sd-card.sh -f 1OBcPjdZG-vug5Qyq2tYF6zjtVBQffbsQ
#
# after setting them, just assign to an env var for child shell scripts to use
export DCGID="${fileid}"

# location where the zip + img files are stored:
download_dir="${DCPATH}/image_files"
if [[ "${DCDOWNLOADDIR}" != "" ]]; then
    download_dir="${DCDOWNLOADDIR}"
fi
# mount path where the hdd partition 2 mounts on your host:
export DCMOUNTPATH="${DCPATH}/dcdisk"
# set resize to max available space by default
export DCGBTOADD="max"
# set to your user before running
if [[ "${DCUSER}" == "" ]]; then
    export DCUSER="jay"
fi

burn_enabled="1"
download_enabled="1"
# try custom file id's with:
# ./burn-image-to-sd-card.sh -f GOOGLE_DRIVE_FILE_ID
if [[ "${DCGID}" != "" ]]; then
    fileid="${DCGID}"
fi
if [[ "${DCIMAGE}" != "" ]]; then
    dcimage="${DCIMAGE}"
fi

# argument parsing code from:
# https://medium.com/@Drew_Stokes/bash-argument-parsing-54f3b81a6a8f
PARAMS=""
while (( "$#" )); do
  case "$1" in
    -i|--install)
        burn_enabled="0"
        download_enabled="0"
        shift 1
        ;;
    # download from a custom image zip from google drive by this file id
    -f|--google-fileid)
        if [[ "${2}" == "" ]]; then
            err "missing google file id"
            exit 1
        fi
        fileid="${2}"
        export DCGID="${2}"
        shift 2
        ;;
    # during image backup, you can name the zipped up image,
    # please use it again to ensure
    # the unzipped file image is correct
    -x|--extracted-image-name)
        if [[ "${2}" == "" ]]; then
            err "missing extracted image name"
            exit 1
        fi
        export DCIMAGENAME="${2}"
        shift 2
        ;;
    -B|--build-base)
        export DCGBTOADD="10"
        shift 1
        ;;
    -t|--docker-registry-url)
        if [[ "${2}" == "" ]]; then
            err "missing docker registry url"
            exit 1
        fi
        export DCDOCKERREGISTRY="${2}"
        shift 2
        ;;
    -e|--docker-user)
        if [[ "${2}" == "" ]]; then
            err "missing docker user for private registry"
            exit 1
        fi
        export DCDOCKERUSER="${2}"
        shift 2
        ;;
    -w|--docker-password)
        if [[ "${2}" == "" ]]; then
            err "missing docker password for private registry"
            exit 1
        fi
        export DCDOCKERPASSWORD="${2}"
        shift 2
        ;;
    -S|--splunk-host)
        if [[ "${2}" == "" ]]; then
            err "missing splunk host"
            exit 1
        fi
        export DCSPLUNKHOST="${2}"
        shift 2
        ;;
    -r|--rclocal-path)
        if [[ ! -e ${2} ]]; then
            err "unable to find rc.local path to -r <file>: ${2}"
            exit 1
        fi
        export DCSTARTUP="${2}"
        shift 2
        ;;
    -g|--gitrepo)
        if [[ ${2} == "" ]]; then
            err "missing github repo arg: -g https://github.com/jay-johnson/donkeycar.git"
            exit 1
        fi
        dcrepo="${2}"
        shift 2
        ;;
    -b|--gitbranch)
        if [[ ${2} == "" ]]; then
            err "missing github branch arg: -b dev"
            exit 1
        fi
        dcbranch="${2}"
        shift 2
        ;;
    -d|--debug)
        export DCDEBUG="1"
        shift 1
        ;;
    --) # end argument parsing
        shift
        break
        ;;
    -*|--*=) # unsupported flag detected
        err "usage error: unsupported flag ${1} detected"
        err ""
        err "Download, burn, resize, mount, deploy, unmountwith:"
        err "usage: ./burn-image-to-sd-card.sh"
        err ""
        err "Mount, deploy, unmount with:"
        err "usage: ./burn-image-to-sd-card.sh -i"
        err ""
        exit 1
        ;;
    *) # preserve positional arguments
        PARAMS="$PARAMS $1"
        shift
      ;;
  esac
done
# set positional arguments in their proper place
eval set -- "$PARAMS"

export DCREPO="${dcrepo}"
export DCBRANCH="${dcbranch}"
# temp storage pathing for download and extraction:
export DCGDOWNLOADPATH="${download_dir}/google-fileid-${DCGID}.zip"
export DCIMAGE="${download_dir}/google-fileid-${DCGID}.img"

if [[ ! -e ${download_dir} ]]; then
    mkdir -p -m 776 ${download_dir}
    if [[ ! -e ${download_dir} ]]; then
        err "failed to create download directory - please create it manually and retry:"
        err "mkdir -p -m 776 ${download_dir}"
        exit 1
    fi
fi

anmt "checking ${DEVICE} partitions"
parted ${DEVICE} print free
inf ""

if [[ "${download_enabled}" == "1" ]]; then
    anmt "ensuring ${DCGID} image zip is downloaded from google drive"
    anmt "${DCPATH}/download-google-drive-dc-img.sh ${fileid} ${DCIMAGE}"
    ${DCPATH}/download-google-drive-dc-img.sh ${fileid} ${DCIMAGE}
    if [[ "$?" != "0" ]]; then
        err "failed to download ${DCGID} as local file: ${DCIMAGE}"
        exit 1
    else
        good "image download and extraction complete"
        ls -lrth ${DCIMAGE}
    fi
    if [[ ! -e ${DCIMAGE} ]]; then
        err "failed to find downloaded image: ${DCIMAGE}"
        exit 1
    fi

    anmt "opening image for manual inspection:"
    chmod 666 ${DCIMAGE}
else
    good " - skipping download image"
fi

if [[ "${burn_enabled}" == "1" ]]; then
    anmt "burning ${DCIMAGE} to sd card: ${DEVICE}"
    # create a backup from a previously burned sd card with:
    # dd if=${DEVICE} of=~/my-donkey-car.img bs=512 count=<last sector> status=progress
    if [[ "${DCDEBUG}" == "1" ]]; then
        dd if=${DCIMAGE} of=${DEVICE} bs=512 status=progress
    else
        dd if=${DCIMAGE} of=${DEVICE} bs=512 status=none
    fi
    if [[ "$?" != "0" ]]; then
        err "failed to burn ${DCIMAGE} to sd card: ${DEVICE}"
        inf "dd if=${DCIMAGE} of=${DEVICE} bs=512 status=progress"
        exit 1
    fi
    good "done burning ${DCIMAGE} to sd card: ${DEVICE}"
    inf ""
    parted ${DEVICE} print free
    inf ""

    anmt "resizing sd card ${DEVICE} with capacity: ${DCGBTOADD} GB more on the device: ${DCPATH}/root-resize-sd-card.sh"
    ${DCPATH}/root-resize-sd-card.sh ${DEVICE} ${DCGBTOADD}
    if [[ "$?" != "0" ]]; then
        err "failed to resize image on sd card: ${DEVICE}"
        inf "${DCPATH}/root-resize-sd-card.sh"
        exit 1
    fi
    good "done resizing sd card: ${DEVICE}"
else
    good " - skipping burn to sd card step"
fi

anmt "checking partitions:"
parted ${DEVICE} print free
inf ""

${DCPATH}/mount-sd-card.sh
if [[ "$?" != "0" ]]; then
    err "failed to mount sd card to: ${DEVICE} to ${DCMOUNTPATH}"
    inf "${DCPATH}/mount-sd-card.sh"
    exit 1
else
    good "mounted ${DEVICE} to ${DCMOUNTPATH}"
fi

last_status=0
if [[ "${DCDEPLOY}" == "" ]]; then
    anmt "running included donkey car deployment tool: ${DCPATH}/deploy.sh"
    ${DCPATH}/deploy.sh
    last_status=$?
else
    anmt "running customer donkey car deployment tool: ${DCDEPLOY}"
    if [[ ! -e ${DCDEPLOY} ]]; then
        err "unable to find custom deploy script with env var: DCDEPLOY=${DCDEPLOY}"
        exit 1
    fi
    ${DCDEPLOY}
    last_status=$?
fi
if [[ "${last_status}" != "0" ]]; then
    err "failed to deploy custom sd card to: ${DCMOUNTPATH}"
    exit 1
fi

# get the ssh pub key before unmounting
pub_key=$(cat ${DCMOUNTPATH}/root/.ssh/id_rsa.pub)

${DCPATH}/unmount-sd-card.sh
if [[ "$?" != "0" ]]; then
    err "failed to unmount sd card: ${DEVICE} from ${DCMOUNTPATH}"
    inf "${DCPATH}/unmount-sd-card.sh"
    exit 1
else
    good "unmounted ${DEVICE} from ${DCMOUNTPATH}"
fi

echo ""
anmt "please confirm this ssh key has the correct access to the github repo:"
anmt "${DCREPO}"
echo "${pub_key}"
echo ""
anmt "example clone:"
echo "git clone ${DCREPO} /opt/dc"
echo ""

date +"%Y-%m-%d %H:%M:%S"
good "new donkey car image ready for use"

exit 0
