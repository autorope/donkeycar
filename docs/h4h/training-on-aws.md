Training on AWS
===============

Access to AWS Instance
----------------------

Copy your public ssh key to the instance using the `ssh-copy-id`
command. This requires a valid password.

```
$ ssh-copy-id ec2-user@ec2-118.123.83.101.eu.aws.amazon.com
```

Add instance details to `~/.ssh/config`

```
Host donkey-trainer
HostName 40.87.58.79
User ec2-user
Port 22
IdentityFile ~/.ssh/id_rsa
```

Managing Training Data
----------------------

Training data (pictures with corresponding angle and trottle) is
stored on the server under `~/mydonkey/sessions` in a directories
named with timestamps.

After completing a session it is recommended to rename the session
directory with a more descriptive name e.g. `mikkel-br1` for the first
round of training data collected from the course in the boardroom by
Mikkel.

*NOTE:* All the session files are owned by root, because docker runs
 as root. You therefore need to either use `sudo` or run the below
 commands from within the server instance (see docker instructions).

```
laptop:~/mydonkey/sessions$ mv 2017_05_23__07_18_46_PM mikkel-br1
```

Open the training data using the web interface on the server to see
the pictures with the corresponding angle and trottle and remove
pictures that should not be part of the training set. For instance
pictures from the beginning or end where the car is standing still
(trottle = 0) or when it is facing an obstacle.

Compress and copy the training set to the AWS instance.

```
laptop:~/mydonkey/sessions$ tar cf mikkel-br1.tar.gz -z mikkel-br1/
laptop:~/mydonkey/sessions$ scp mikkel-br1.tar.gz donkey-trainer:/root/mydonkey/sessions
```

Running Training
----------------

Uncompress and start training by giving training sessions and pilot
name as commandline parameters.

Several sessions can be combined if desired.

```
laptop:~$ ssh donkey-trainer
aws:~$ cd mydonkey/sessions
aws:~/mydonkey/sessions$ tar xf mikkel-br1.tar.gz
aws:~/donkey$ python scripts/train.py --sessions mikkel-br1,schalk-br1 --name mypilot
```

Copy Pilot to Raspberry Pi
--------------------------

Copy the pilot to your Raspberry Pi.
```
laptop:~$ scp donkey-trainer:/root/mydonkey/models/mypilot.hdf5 ~/mydonkey/models
laptop:~$ scp ~/mydonkey/models/mypilot.hdf5 rpi:/home/pi/mydonkey/models
```
