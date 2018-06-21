# What is a Part

A part Python class that wraps a functional component of a vehicle.
These include:
* Sensors - Cameras, Lidar, Odometers, GPS ...
* Actuators - Motor Controllers
* Pilots - Lane Detectors, Behavioral Cloning models, ...
* Controllers - Web based or Bluetooth.
* Stores - Tub, or a way to save data.

Here is an example how to use the PiCamera part to publish an image in the
'cam/img' channel on every drive loop.

```python
V = dk.Vehicle()

#initialize the camera part
cam = PiCamera()

#add the part to the vehicle.
V.add(cam, outputs=['cam/img'])

V.start()
```

## Anatomy of a Part

All parts share a common structure so that they can all be run by the vehicles
drive loop. Here is an example of a part that will accept a number, multiply
it by a random number and return the result.

```python
import random

class RandPercent:
    def run(self, x):
        return x * random.random()
```

Now to add this to a vehicle:

```python
V = dk.Vehicle()

#initialize the channel value
V.mem['const'] = 4

#add the part to read and write to the same channel.
V.add(RandPercent, inputs=['const'], outputs=['cost'])

V.start(max_loops=5)
```


### Threaded Parts
For a vehicle to perform well the drive loop must execute 10-30 times per
second so slow parts should be threaded to avoid holding up the drive loop.

A threaded part needs to define the function that runs in the separate thread
and the function to call that will return the most recent values quickly.

Here's an example how to make the RandPercent part threaded if the run
function too a second to complete.

```python
import random
import time

class RandPercent:
    self.in = 0.
    self.out = 0.
    def run(self, x):
        return x * random.random()
        time.sleep(1)

    def update(self):
        #the funtion run in it's own thread
        while True:
            self.out = self.run(self.in)

    def run_threaded(self, x):
        self.in = x
        return self.out

```




* `part.run` : function used to run the part
* `part.run_threaded` : drive loop function run if part is threaded.
* `part.update` : threaded function
* `part.shutdown`
