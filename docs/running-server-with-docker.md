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
