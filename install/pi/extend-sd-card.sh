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

fdisk -l $DEVICE$PARTNR >> /dev/null 2>&1 || (echo "could not find device $DEVICE$PARTNR - please check the name" && exit 1)

CURRENTSIZEB=`fdisk -l $DEVICE$PARTNR | grep "Disk $DEVICE$PARTNR" | cut -d' ' -f5`
CURRENTSIZE=`expr $CURRENTSIZEB / 1024 / 1024`
# So get the disk-informations of our device in question printf %s\\n 'unit MB print list' | parted | grep "Disk /dev/sda we use printf %s\\n 'unit MB print list' to ensure the units are displayed as MB, since otherwise it will vary by disk size ( MB, G, T ) and there is no better way to do this with parted 3 or 4 yet
# then use the 3rd column of the output (disk size) cut -d' ' -f3 (divided by space)
# and finally cut off the unit 'MB' with blanc using tr -d MB
MAXSIZEMB=`printf %s\\n 'unit MB print list' | parted | grep "Disk ${DEVICE}" | cut -d' ' -f3 | tr -d MB`

echo "[ok] would/will resize to from ${CURRENTSIZE}MB to ${MAXSIZEMB}MB "

if [[ "$APPLY" == "apply" ]] ; then
    anmt "ok applying resize operation.."
    anmt "parted -s ${DEVICE} resizepart ${PARTNR} ${MAXSIZEMB}"
    parted -s ${DEVICE} resizepart ${PARTNR} ${MAXSIZEMB}
    if [[ "$?" != "0" ]]; then
        err "failed to resize partition with: parted -s ${DEVICE} resizepart ${PARTNR} ${MAXSIZEMB}"
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
