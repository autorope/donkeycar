Running the Server with Docker
==============================

Install Docker
--------------

On Ubuntu/Debian the package is named `docker.io`.

```
$ sudo apt install docker.io
```

Add your user to docker group and login again.

```
$ sudo usermod -a -G docker <username>
```
Then exit and login again.

Get the Server Image
--------------------

The image can be built with the Dockerfile in the root of this
repository or pulled from docker hub and retagged.

```
$ docker build .

OR

$ docker pull mschristiansen/donkey
$ docker tag mschristiansen/donkey donkey
```

Run the Server Image
--------------------

Use `start-server.sh` from root of this repository.

```
$ bash start-server.sh
```

Running Commands on the Server
------------------------------

Use `docker exec` to open a shell "inside" a running instance of the
server or run a shell in a new instance of the server.

```
$ docker exec -it donkey /bin/bash

OR

$ bash start-server.sh -d
```

The web interface should now be accessible with your browser on
(http://localhost:8887)


Make Server Accessible
----------------------

The server by default runs on port 8887 which must be made accessible
from the Raspberry Pi. This can be done using `ufw` to manage your
iptables configuration.

```
$ sudo apt install ufw    # If not already installed
$ sudo ufw enable
$ sudo ufw allow 8887/tcp
$ sudo ufw status         # Check status
$ sudo ufw reset          # Close port and disable
```

You should now be able to open the web interface from anywhere on the
wifi e.g. from your phone using (http://<server IP address>:8887).

(Check IP address with `$ ifconfig`)
