![travis](https://travis-ci.org/wroscoe/donkey.svg?branch=dev)

# Donkey: a self driving library and control platform for small scale DIY 
vehicles. 

Donkey is minimalist and modular self driving library written in Python. It is 
developed for hobbiests with a focus on allowing fast experimentation and easy 
community contributions.  

#### Build the standard Donkey2 (http://www.donkeycar.com) ($200 + 2 hours)

#### Use Donkey if you want to:
* Make an RC car drive its self.
* Compete in self driving races like [DIY Robocars](diyrobocars.com)
* Use existing autopilots to drive your car.
* Use community datasets to create, improve and test autopilots that other 
people can use.  

#### Features:
* Data logging of image, steering angle, & throttle outputs. 
* Web based car controls.
* Community contributed driving data and autopilots.
* Hardware CAD designs for optional upgrades.


### Getting started. 
After building and calibrating the standard Donkey2 you can drive your car 
with your phone by running the following via ssh on the cars Raspberry Pi. 

```
python examples/donkey2.py
```
Now you can control your car by going to `<ip_address_of_your_pi>:8887/drive`
