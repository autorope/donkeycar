#!/bin/bash
set -e

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
  echo "[ok] applying resize operation.."
  parted -s ${DEVICE} resizepart ${PARTNR} ${MAXSIZEMB}
  echo "[done]"
else
  echo "[WARNING]!: Sandbox mode, i did not size!. Use 'apply' as the 3d parameter to apply the changes"
fi
