#!/bin/bash
set -e

# stack overflow on this:
# https://serverfault.com/questions/870594/resize-partition-to-maximum-using-parted-in-non-interactive-mode
#
# blog used to help make this:
# https://geekpeek.net/resize-filesystem-fdisk-resize2fs/

if [[ "${DCPATH}" == "" ]]; then
    export DCPATH="."
fi
if [[ -e ${DCPATH}/files/bash_colors.sh ]]; then
    source ${DCPATH}/files/bash_colors.sh
fi

if [[ $# -eq 0 ]] ; then
    echo 'please tell me the device to resize as the first parameter, like /dev/sda'
    exit 1
fi

if [[ $# -eq 1 ]] ; then
    echo 'please tell me the partition number to resize as the second parameter, like 1 in case you mean /dev/sda1 or 4, if you mean /dev/sda2'
    exit 1
fi

DEVICE=$1
PARTNR=$2
APPLY=$3
NUM_GB_TO_ADD=$4

fdisk -l $DEVICE$PARTNR >> /dev/null 2>&1 || (echo "could not find device $DEVICE$PARTNR - please check the name" && exit 1)

CURRENTSIZEB=`fdisk -l $DEVICE$PARTNR | grep "Disk $DEVICE$PARTNR" | cut -d' ' -f5`
CURRENTSIZE=`expr $CURRENTSIZEB / 1024 / 1024`
# So get the disk-informations of our device in question printf %s\\n 'unit MB print list' | parted | grep "Disk /dev/sda we use printf %s\\n 'unit MB print list' to ensure the units are displayed as MB, since otherwise it will vary by disk size ( MB, G, T ) and there is no better way to do this with parted 3 or 4 yet
# then use the 3rd column of the output (disk size) cut -d' ' -f3 (divided by space)
# and finally cut off the unit 'MB' with blanc using tr -d MB
MAXSIZEMB=`printf %s\\n 'unit MB print list' | parted | grep "Disk ${DEVICE}" | cut -d' ' -f3 | tr -d MB`
USESIZEMB=${MAXSIZEMB}

# if no size is set... max the device's storage capacity
if [[ "${NUM_GB_TO_ADD}" == "" ]] || [[ "${NUM_GB_TO_ADD}" == "max" ]] || [[ "${NUM_GB_TO_ADD}" == "Max" ]]; then
    # setting this to empty will activate the original mode which is to
    # max out the storage capacity for the 2nd partition
    # this however makes backing up your new base image into a huge img file on disk...
    # so this new capacity flag was added
    anmt "will resize from ${CURRENTSIZE}MB to a max capacity of ${USESIZEMB}MB "
else
    let USESIZEMB="(${CURRENTSIZEB} + ($NUM_GB_TO_ADD * 1073741824)) / 1024 / 1024"
    anmt "adding ${NUM_GB_TO_ADD}G to ${DEVICE}2 from ${CURRENTSIZE}MB to ${USESIZEMB}MB of ${MAXSIZEMB}MB available"
fi

if [[ "$APPLY" == "apply" ]] ; then
    anmt "starting resize operation:"
    anmt "parted -s ${DEVICE} resizepart ${PARTNR} ${USESIZEMB}"
    parted -s ${DEVICE} resizepart ${PARTNR} ${USESIZEMB}
    if [[ "$?" != "0" ]]; then
        err "failed to resize partition with: parted -s ${DEVICE} resizepart ${PARTNR} ${USESIZEMB}"
        err "max MB available: ${MAXSIZEMB}"
        exit 1
    else
        anmt "done - parted"
    fi
    anmt "fixing partitions:"
    anmt "e2fsck -y -f ${DEVICE}2"
    e2fsck -y -f ${DEVICE}2
    if [[ "$?" != "0" ]]; then
        err "failed to e2fsck ${DEVICE}2 with: e2fsck -y -f ${DEVICE}2"
        exit 1
    else
        anmt "done - e2fsck"
    fi
    # this should resize the partition to max out the storage space
    anmt "sleeping to let the disk changes finish"
    sleep 5
    anmt "resize2fs ${DEVICE}2"
    resize2fs ${DEVICE}2
    if [[ "$?" != "0" ]]; then
        err "failed to resize2fs ${DEVICE}2 with: resize2fs ${DEVICE}2"
        exit 1
    else
        anmt "done - resize"
    fi
else
    err "[WARNING]!: Sandbox mode, did not detect size correctly!. Use 'apply' as the 3rd parameter to apply the changes"
    exit 1
fi

good "done - extend-sd-card.sh"

exit 0
