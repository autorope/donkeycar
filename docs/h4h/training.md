Training
========

Connect the Raspberry Pi to the Server
--------------------------------------

SSH to the Raspberry Pi and make it connect to the server which must
be running and accessible on the WIFI.

On the Raspberry Pi edit `start.sh` with the IP address of your server
then run the script.

The script takes a few seconds to run, but once it connects to your
server you will see an acknowledgement in stdout from the server and
your vehicle (donkey) will be visible in the web interface.

Gather Training Data
--------------------

Use the web interface to drive the vehicle around. This is easiest
done by using the web interface from a phone while walking behind the
vehicle. Set the trottle speed to constant at as low a speed as
possible and concentrate on keeping the vehicle on the track.

You will later be able to edit the training data to remove crashes
etc, but it is easier and more fun to generate a good data set by
driving rather than editing.

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

Running Training
----------------

start training by giving training sessions and pilot name as
commandline parameters. Several sessions can be combined if desired.

```
laptop:~/donkey$ python scripts/train.py --sessions mikkel-br1,schalk-br1 --name mypilot
```

The sessions are used by Tensorflow to train a neural network with the
pictures as inputs and corresponding angle/trottle as output.

While training is running it shows `epoch`, which is how many times
the network has been trained on the session data. Training will end
once the network becomes stable between epochs or after 100
iterations.

For each iteration the loss values improve which can be interpretated
as accuracy of the model. Smaller is better.


Copy Pilot to Raspberry Pi
--------------------------

Once training has ended copy the pilot to your Raspberry Pi and start
the server.

```
laptop:~$ scp ~/mydonkey/models/mypilot.hdf5 rpi:/home/pi/mydonkey/models
```

On the web interface you can now select a pilot for your vehicle. It
is advisable initially to only give the pilot control over the angle
and manually control the trottle.


Training on AWS
===============

Access to AWS Instance
----------------------

Copy your public ssh key to the instance using the `ssh-copy-id`
command. This requires valid credentials and a server address.

```
$ ssh-copy-id ec2-user@ec2-118.123.83.101.eu.aws.amazon.com
```

Add instance details to `~/.ssh/config`

```
Host donkey-trainer
HostName ec2-118.123.83.101.eu.aws.amazon.com
User ec2-user
Port 22
IdentityFile ~/.ssh/id_rsa
```

Compress and copy the training set to the AWS instance.

```
laptop:~/mydonkey/sessions$ tar cf mikkel-br1.tar.gz -z mikkel-br1/
laptop:~/mydonkey/sessions$ scp mikkel-br1.tar.gz donkey-trainer:/root/mydonkey/sessions
```

Uncompress on AWS instance.

```
laptop:~$ ssh donkey-trainer
aws:~$ cd mydonkey/sessions
aws:~/mydonkey/sessions$ tar xf mikkel-br1.tar.gz
```

Follow normal instructions for training above.
