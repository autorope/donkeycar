## Automation for Customizing Your Donkey Car OS Install

This guide is for [Donkey Car owners](https://www.donkeycar.com/) looking to automate their sd card installs with controls for automating the initial boot up. It has only been tested on Ubuntu.

[![Automation for Customizing Your Donkey Car OS Install](https://asciinema.org/a/249687.svg)](https://asciinema.org/a/249687?autoplay=1)

1. Set User and sd card device name

please be careful to use the correct device path or you may delete something you do not want to delete.

```
sudo su
export DCUSER=YOUR_USER_IN_UBUNTU
export DEVICE=/dev/sdf
```

2. Set the Wifi SSID and Password

```
export WIFINAME="WIFI_SSID_NAME"
export WIFIPASSWORD="WIFI_PASSWORD"
```

3. Burn the Image as Root

This will download, burn, resize to maximize storage, mount, deploy the latest custom artifacts (including support for installing docker and an rc.local file), and then unmount the latest donkey car release image as the root user with the sd card inserted in to the **DEVICE** sd reader. The newly-burned filesystem will be mounted at **./dcdisk** and then the **deploy.sh** script will run to install all additional, custom files to the sd card's new OS before unmounting the sd card for use on a donkey car or just in a rasberry pi 3b+.

```
# please run as root:
./burn-image-to-sd-card.sh
```

Workflow ordering and specific files in case you want to make custom modifications for your donker car os on your own:

[./burn-image-to-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/burn-image-to-sd-card.sh) calls:

    a) [./download-google-drive-dc-img.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/download-google-drive-dc-img.sh)

    b) [./root-resize-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/root-resize-sd-card.sh)

    c) [./extend-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/extend-sd-card.sh)

    d) [./mount-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/mount-sd-card.sh)

    e) [./deploy.sh or custom script set before starting with: export DCDEPLOY=PATH_TO_YOUR_DEPLOY_TOOL](https://github.com/autorope/donkeycar/blob/dev/install/pi/deploy.sh)

    f) [./unmount-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/unmount-sd-card.sh)

### Cutomize Startup Actions with an rc.local

Edit the [./files/rc.local](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/rc.local) and redeploy with [./just-deploy-build-to-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/just-deploy-build-to-sd-card.sh)

### Setup your Donkey Car with a Private Docker Registry

Edit the [./files/docker-daemon.json](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/docker-daemon.json) if you want to add a custom, private docker registry for pulling images.

### Redeploy Files to an Existing SD Card without Downloading, Reformatting or Burning the SD Card

[![Redeploy Files to an Existing SD Card without Downloading, Reformatting or Burning the SD Card](https://asciinema.org/a/249682.svg)](https://asciinema.org/a/249682?autoplay=1)

If you have already burned an image to the sd card, then you can skip the image download, extraction, burning, and resizing to just deploy files to an existing sd card's OS image with the command:

```
# please run as root:
./just-deploy-build-to-sd-card.sh
```

### Deploy Your Own Startup rc.local and GitHub Repo as arguments

Please note, these optional command arguments also work with the full **burn-image-to-sd-card.sh** script too.

```
./just-deploy-build-to-sd-card.sh \
    -r CUSTOM_RCLOCAL_PATH \
    -g CUSTOM_GITHUB_REPO_URL \
    -b CUSTOM_GITHUB_BRANCH \
    -e DOCKER_REGISTRY_USER \
    -w DOCKER_REGISTRY_PASSWORD \
    -t DOCKER_REGISTRY_ADDRESS
```

### Use Your Own Deploy Script to Prepare the Donkey Car OS

You can build and use your own deploy script with both **burn-image-to-sd-card.sh** and **just-deploy-build-to-sd-card.sh** by setting the environment variable var **DCDEPLOY** before running the commands as root:

```
export DCDEPLOY=PATH_TO_CUSTOM_DEPLOY_SCRIPT
./just-deploy-build-to-sd-card.sh
# or during a full download + burn + resize:
# ./burn-image-to-sd-card.sh
```

### Delete Partitions For Burning a New Build - Start Over

If you need to delete the sd card manually, you can and use the commands below (please be careful!):

#### Delete SD Card Contents

```
./_delete-sd-card.sh DEVICE
# like: ./_delete-sd-card.sh /dev/sdf
```

#### Manually Delete SD Card Partitions

1. Check the Device Before Deleting Something Incorrectly

```
echo "${DEVICE}"
```

2.  Confirm the 2nd Partition Is Correct

```
parted ${DEVICE} print free
```

3.  Delete the 2nd Partition on the Correct Device

```
parted ${DEVICE} rn 2
```

### Install Docker After the Logging into the Donkey Car

SSH into the donkey car host and install docker with the command:

[/opt/dc/files/docker-install.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/docker-install.sh)

## Install Packages and Update Your Donkey Car on Startup

On startup the donkey car OS uses the file: [/etc/rc.local](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/rc.local) to run custom actions on boot. You can customize any of these files to install and update your donkey car after burning the sd card.

By default, the **rc.local** will run the following scripts if they are found on the filesystem:

1. If [/opt/first_time_install.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/first_time_install.sh) is found it will install packages

2. If [/opt/run_updater.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/run_updater.sh) is found it will run any updates
