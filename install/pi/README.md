## Automation for Customizing Your Donkey Car OS Install

This guide is for [Donkey Car owners](https://www.donkeycar.com/) looking to automate their sd card installs with controls for automating the initial boot up. It has only been tested on Ubuntu.

[![Automation for Customizing Your Donkey Car OS Install](https://asciinema.org/a/249781.svg)](https://asciinema.org/a/249781?autoplay=1)

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

#### Optional Environment Variables to Set

##### GitHub Repository and Branch to Clone and Use

```
export DCREPO=GITHUB_URL
export DCBRANCH=GITHUB_BRANCH
```

##### Docker Credentials for a Private Docker Registry

```
export DCDOCKERUSER=DOCKER_USER
export DCDOCKERPASSWORD=DOCKER_PASSWORD
export DCDOCKERREGISTRY=DOCKER_REGISTRY_ADDRESS_WITH_PORT
```

##### Splunk Host for Publishing from a Donkey Car

```
export DCSPLUNKHOST="192.168.0.100"
```

3. Burn the Image as Root

This will download, burn, resize to maximize storage, mount, deploy the latest custom artifacts (including support for installing docker and an rc.local file), and then unmount the latest donkey car release image as the root user with the sd card inserted in to the **DEVICE** sd reader. The newly-burned filesystem will be mounted at **./dcdisk** and then the **deploy.sh** script will run to install all additional, custom files to the sd card's new OS before unmounting the sd card for use on a donkey car or just in a rasberry pi 3b+.

```
# please run as root:
./burn-image-to-sd-card.sh
```

Workflow ordering and specific files in case you want to make custom modifications for your donkey car os on your own:

[./burn-image-to-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/burn-image-to-sd-card.sh) calls:

3a) [./download-google-drive-dc-img.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/download-google-drive-dc-img.sh)

3b) [./root-resize-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/root-resize-sd-card.sh)

3c) [./extend-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/extend-sd-card.sh)

3d) [./mount-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/mount-sd-card.sh)

3e) [./deploy.sh or custom script set before starting with: export DCDEPLOY=PATH_TO_YOUR_DEPLOY_TOOL](https://github.com/autorope/donkeycar/blob/dev/install/pi/deploy.sh)

3f) [./unmount-sd-card.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/unmount-sd-card.sh)

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
    -t DOCKER_REGISTRY_ADDRESS \
    -S SPLUNK_HOST
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

### SSH into the Donkey Car OS


```
# ssh -i ./files/id_rsa pi@d1.example.com
ssh -i ./files/id_rsa pi@DONKEY_CAR_IP
```

Or with the ssh login tool:

```
./ssh-into-dc.sh d1.example.com
```

### Install Docker After the Logging into the Donkey Car

SSH into the donkey car host and install docker

#### Run the Docker Installer

[/opt/dc/files/docker-install.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/docker-install.sh)

## Install Packages and Update Your Donkey Car on Startup

On startup the donkey car os uses the file: [/etc/rc.local](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/rc.local) to run custom actions on boot. You can customize any of these files to install and update your donkey car after burning the sd card.

By default, the **rc.local** will run the following scripts if they are found on the filesystem:

1. If [/opt/first_time_install.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/first_time_install.sh) is found it will install packages

2. If [/opt/run_updater.sh](https://github.com/autorope/donkeycar/blob/dev/install/pi/files/run_updater.sh) is found it will run any updates

### Donkey Car Docker Images

Please note the donkey car images take a long time to build and >2 GB HDD space so please plan accordingly when using these images and they use python 3.7 as the default runtime.

Please follow the [Running Donkey Car on a Raspberry Pi within Docker Images Readme](https://github.com/jay-johnson/donkeycar/tree/d1/install/pi/docker#running-donkey-car-on-a-raspberry-pi-within-docker-images) for more details on how to customize your own docker images.

### Set up Automatic Donkey Car Log Publishing to Splunk

By following this guide's installer your donkey car os is ready for log and system metric aggregation using [Fluent Bit listening on TCP 24224](https://docs.fluentbit.io/manual/v/1.1/input/tcp) that automatically [forwards to a remote-hosted Splunk HEC Rest API](https://docs.fluentbit.io/manual/v/1.1/output/splunk).

![IoT log and metric pipeline using Fluent Bit and Splunk - you can start your log search with: index=dc](https://i.imgur.com/SsVhZQ9.png "IoT log and metric pipeline using Fluent Bit and Splunk")

#### Where do I get splunk?

There is an included, dockerized splunk container that runs from the base of the repository. Please note, it requires having docker-compose to use:

```
./compose/start.sh -s ./compose/splunk/splunk.yaml
```

Use these default splunk login credentials with the login url below:

- user **pi**
- password **123321**

http://logs.example.com:8000/en-US/app/search/search?q=search%20index%3Ddc

##### Login to Splunk

##### Publish Logs to Splunk from a Donkey Car

Please run this from a donkey car that has the Fluent Bit agent running with a valid HEC Splunk Token:

```
/opt/dc/install/pi/files/test_fluent_bit.py
```

## Search for Logs in Splunk

By default, the install, updater, repository builder, docker container builder, and any apps using the donkey car logger are forwarded to Splunk and searchable from the index:

```
index=dc
```

#### Search for Install Logs

Search for the sd card's first time installer logs with:

```
index=dc AND sd.install
```

#### Search for Update Logs

Search for the sd card's updater logs with:

```
index=dc AND sd.update
```

#### Search for Repository Build and Install Logs

Search for the sd card's repository builder logs with:

```
index=dc AND sd.repo
```

#### Search for Docker Container Build Logs

Search for the sd card's docker container build logs with:

```
index=dc AND docker.build
```

#### Get the HEC Token from a Browser

The burn tool automatically installs the Splunk HEC Token named **dc-token** into an sd card. You can also view the HEC token from within Splunk here:

http://logs.example.com:8000/en-US/manager/search/http-eventcollector

#### View the HEC Token from the included Splunk container

```
# run from the base of the repo:
./donkeycar/splunk/get_token.sh
```

##### HEC Token Updates

If you need to roll the cars to a new HEC token, then please update the splunk token manually in all donkey car sd cards at this file location:

```
/opt/fluent-bit-includes/fluent-bit-log.yaml
...
[OUTPUT]
    ...
    Name            splunk
    ...
    Splunk_Token    NEW_SPLUNK_TOKEN
```

### Debugging Splunk Token Issues

Here is a python command for quickly testing the Fluent Bit's Splunk config file ([installed at /opt/fluent-bit-includes/fluent-bit-log.yaml](https://github.com/autorope/donkeycar/blob/d1/install/pi/files/fluent-bit-log.yaml)) works with your Splunk HEC Token. Please run this from a donkey car ssh session:

```
source /opt/venv/bin/activate
python -c "from donkeycar.log import get_log; import datetime; \
    log = get_log('testing', config='/opt/dc/donkeycar/splunk/log_config.json'); \
    log.info(
        'hello from dc1 sent at: {}'.format(
            datetime.datetime.utcnow()))"
```

