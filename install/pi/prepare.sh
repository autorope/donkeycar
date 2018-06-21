#!/usr/bin/env bash

#Script to setup pi disk after base rpi image.

MEDIA=/media/$USER
BOOT=$MEDIA/boot
ROOTFS=$MEDIA/rootfs

sudo touch $BOOT/ssh

#enable camera
echo "start_x=1" | sudo tee -a $BOOT/config.txt
echo "gpu_mem=128" | sudo tee -a $BOOT/config.txt

#enable i2c
echo "i2c-dev" | sudo tee -a $ROOTFS/etc/modules

#Change hostname
hostn=$(cat $ROOTFS/etc/hostname)
echo "Existing hostname is $hostn"
echo "Enter new hostname: "
read newhost

#change hostname in /etc/hosts & /etc/hostname
sudo sed -i "s/$hostn/$newhost/g" $ROOTFS/etc/hosts
sudo sed -i "s/$hostn/$newhost/g" $ROOTFS/etc/hostname
echo "Your new hostname is $newhost"

# setup default wifi config
sudo truncate -s 0 $ROOTFS/etc/wpa_supplicant/wpa_supplicant.conf
cat <<'EOF' | sudo tee $ROOTFS/etc/wpa_supplicant/wpa_supplicant.conf
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="network_name"
    psk="password"
}
EOF