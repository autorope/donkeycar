## Docker Compose Files

### Host Compose Files

Note: Mac OS X users will need to add **/data/dc** as a supported docker volumes (Docker -> Preferences -> File Sharing -> +).

```
cd compose
```

#### Minio

[Minio](https://min.io/) is an s3 server for storing your own AI datasets and image/file uploads. Instead of paying per byte, you can host an s3 server yourself for free. Start pushing images out of your donkey car and pulling down training dataset into your car for training ai/ml models after you clean the datasets up outside the car (where you have more cpu horsepower).

1. Start

```
./start.sh -m ./minio/minio.yaml
```

2. Login from a browser with **dcpi** and **raspberry**

http://0.0.0.0:9001/

3. Stop

```
./stop.sh -m ./minio/minio.yaml
```

#### Splunk

[Splunk](https://www.splunk.com/) is a high-speed log aggregation server that can handle a fleet of donkey cars sending logs to it at once (like at a race!). The included version of splunk is the free tier which gets you a capacity of 500 MB worth of logs per day.

##### How does it work?

Your donkey car will automatically push its install, updater, repository build, and docker container builds directly into splunk for debugging without always needing to have an ssh session to your car (splunk hosts a webapp ui for searching). This log pipeline is built using [Fluent Bit](https://fluentbit.io/), which is automatically installed and enabled as a service in your donkey car's operating system.

1. Start

```
./start.sh -s ./splunk/splunk.yaml
```

2. Login from a browser with **pi** and **123321**

http://0.0.0.0:8000/

3. Stop

```
./stop.sh -s ./splunk/splunk.yaml
```

##### Customize Fluent Bit Forwarding on a Donkey Car

You can customize the log and file forwarding your Donkey car uses by editing the [/opt/fluent-bit-includes/fluent-bit-log.yaml file on your donkey car filesystem](https://github.com/jay-johnson/donkeycar/blob/d1/install/pi/files/fluent-bit-log.yaml) and then restarting the fluent-bit agent with:

```
sudo systemctl restart td-agent-bit
```

For more information on Fluent Bit:

- [Supported Fluent Bit inputs (sources)](https://fluentbit.io/documentation/0.13/input/)
- [Supported Fluent Bit outputs (sinks)](https://fluentbit.io/documentation/0.13/output/)

Please note the [MQTT server](https://fluentbit.io/documentation/0.13/input/mqtt.html) is being explored as a way to push messages to a specific donkey car from a remote client (say for pushing out an "update the car's donkey car build and restart the components").

#### Private Docker Registry

1. Start Registry

```
./start.sh \
    -r ./registry/registry.yaml \
    -e DOCKER_USER -w DOCKER_PASSWORD
```

2. Install Registry on all Hosts including the Donkey Car

Each docker daemon will need to login to the registry before it can pull custom docker images down. Please add the **HOST_IP:5000** to the file: **/etc/docker/daemon.json** and then restart docker (``systemctl restart docker``).

Please ensure the **./registry/daemon.json** is added to the **/etc/docker/daemon.json** file to support logging in.

3. Login to Your Private Docker Registry on all Host including the Donkey Car

```
echo "DOCKER_PASSWORD" | docker login --username ${DOCKER_USER} --password-stdin 0.0.0.0:5000
```
