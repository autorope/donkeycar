# About Donkey

Donkey is a high level self driving library written in Python and capable of 
controlling ackerman or differential drive vehicles. It was developed with a 
focus on enabling fast experimentation and easy contribution.

#### Use Donkey if you want to...

* Build your own small scale self driving car.
* Implement computer vision or neural network based auto-pilots.
* Use an arbitrary number of sensors on your car. 

###Guiding Developement Principles
* **Modularity**: A self driving system is composed of standalone, 
independently configurable modules that can be connected modules.

* **Minimalism**: Each component should be kept short (<100 lines of code). 
Each peice of code should be transparent apon first reading. No black magic, it slows the speed of innovation. 

* **Extensiblity**: New components should be simple to create by following a 
template. 

* **Python**: Keep it simple. 

***These guidelines are nearly copied from [Keras](http://keras.io) because they are so good*** 


## Installation

### Developement version

```bash
git clone https://github.com/wroscoe/donkey donkeycar
pip install -e donkeycar
```

Now create a fake car on your computer to see if it works. 
```bash
donkey createcar --path sdonk --template record_square
cd ~/sdonk
python car.py drive
python car.py train --tub <your_tub_name> --model <your_new_model_name>
```

## Getting started in 30 seconds. 

### Record images from the camera

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

### More examples
You can find more examples in the examples folder.