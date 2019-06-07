### Running Donkey Car on a Raspberry Pi within Docker Images

This guide covers building docker images that work on a donkey car's raspberry pi (tested on 3b+). This is a work in progress and will likely have bug fixes for it in the future.

Please note:

To build a docker image from a raspberry pi, please either wait for [this PR to merge](https://github.com/autorope/donkeycar/pull/384) or you can use [my latest fork using the branch: d1](https://github.com/jay-johnson/donkeycar/tree/d1):

#### Build Docker Images

Please run this from a donkey car OS that has docker installed. Please note, it will take many hours to build and is ~2.1 GB in size so make sure your sd card has enough space.

1. SSH into Donkey Car or an extra Raspberry Pi used for building releases

```
ssh pi@DONKEY_CAR_IP
```

2. Start the Builds in the Background

Because these images take so long to build, it is common to hit the ssh timeouts that interrupt the build so please background the build process to a log file so you can track the status as it builds.

```
cd /opt/dc/install/pi/docker/
./start-build.sh
# watch the build logs on the device:
# tail -f /tmp/docker.log
```

### Automatically Push Successful Docker Images Builds to Your Private Docker Registry

Before building the images with **./start-build.sh**, please export these environment variables to push to your own private docker registry. These must be run from the raspberry pi device before starting the build. This also is works with [Docker Hub](https://hub.docker.com/).

```
export DOCKER_USER=YOUR_DOCKER_USER
export DOCKER_PASSWORD=YOUR_DOCKER_PASSWORD
export DOCKER_REGISTRY=YOUR_DOCKER_REGISTRY
```

For pushing images to [Docker Hub](https://hub.docker.com/) use this for the **DOCKER_REGISTRY**:

```
export DOCKER_REGISTRY=docker.io
```
