![travis](https://travis-ci.org/wroscoe/donkey.svg?branch=dev)

# Donkey: a python self driving library 

Donkey is minimalist and modular self driving library written in Python. It is 
developed for hobbiests with a focus on allowing fast experimentation and easy 
community contributions.  

[Documentation](http://docs.donkeycar.com)

#### Build the standard [Donkey2](http://www.donkeycar.com) ($200 + 2 hours)

#### Use Donkey if you want to:
* Make an RC car drive its self.
* Compete in self driving races like [DIY Robocars](diyrobocars.com)
* Experiment with different driving methods.
* Add parts and sensors to your car.

#### Features:
* Data logging. (images, user inputs, sensor readings) 
* Web or hardware car controls.
* Library of parts and pilots.
* Community contributed driving data.
* Hardware CAD designs for optional upgrades.

### Getting started. 
After building your Donkey2 you can install donkeycar and start driving 
with your phone by running the following via ssh on the cars Raspberry Pi. 

```
pip install donkeycar

donkey createcar --path ~/d2

python car.py drive
```
Now you can control your car by going to `<ip_address_of_your_pi>:8887/drive`
