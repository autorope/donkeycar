# About Donkey

Donkey is a high level self driving library written in Python and capable of 
controlling ackerman or differential drive vehicles. It was developed with a 
focus on enabling fast experimentation and easy contribution.

#### What can you do with Donkey?

* Build your own small scale self driving car.
* Implement computer vision or neural network based auto-pilots.
* Experiement with different sensors on your car. 

### Get started.

1. Build a car.
2. Install the donkeycar libary. `pip install donkeycar`
3. Create the drive script for your car from a template.  `donkey createcar ~/d2`
4. Start driving your car. `python ~/d2/manage.py drive`
5. Control your car in a browser at `<your pi's ip address>:8887` 


### Hello World. 

Here's a drive script that will record images from a camera and 
save them to disk. 

```python

import donkey as dk

V = dk.Vehicle()

#add a camera
cam = dk.parts.PiCamera()
V.add(cam, outputs=['image'], threaded=True)

#record the images
tub = dk.parts.Tub(path='~/mydonkey/gettings_started', 
                   inputs=['image'], 
                   types=['image_array'])
V.add(tub, inputs=inputs)

#start the drive loop
V.start(max_loop_count=100)
```
