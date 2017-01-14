# Donkey: a self driving library and control platform for small scale DIY vehicles. 

Donkey is minimalist and modular self driving library written in Python. It is developed for hobbiests with a focus on allowing fast experimentation and easy community contributions.  

####Use Donkey if you want to:
* [Quickly build your own self driving RC car.](docs/01-build_a_car.md) (~$200 + 5hrs).
* Use existing autopilots to drive your car.
* Use community datasets to create, improve and test autopilots that other people can use.  


#### Library Features:
* Data logging of image, steering angle, & throttle outputs. 
* Wifi car controls (a virtual joystic).
* Community contributed driving data and autopilots.
* Hardware CAD designs for optional upgrades.


### Drive your car
Once you have built your car you can use it like this.

1. Start the default pilot server. `python demos/serve.py`

2. Start your car and connect it to the pilot server. `python demos/drive_pi.py  --remote http://<your_pilot_server_ip>:8887`

3. Go to `<your_pilot_server_ip>:8887` on your phone or computer to start driving your car. 

 Use the [demos](demos) to see how to record driving data, train autopilots and more.
 





