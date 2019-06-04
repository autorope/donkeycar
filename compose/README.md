## Docker Compose Files

### Host Compose Files

Note: Mac OS X users will need to add **/opt/docker_data** to their supported docker volumes.

```
cd compose
```

#### Splunk

1. Start

```
./compose_start.sh -s ./splunk/splunk.yaml
```

2. Login from a browser with **pi** and **123321**

http://0.0.0.0:8000/

3. Stop

```
./compose_stop.sh -s ./splunk/splunk.yaml
```

#### Private Docker Registry

1. Start Registry

```
./compose_start.sh \
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
