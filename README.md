# Donkey: a self driving library and control platform for small scale DIY vehicles. 

Donkey is minimalist and modular self driving library written in Python. It is developed for hobbiests with a focus on allowing fast experimentation and easy community contributions.  

####Use Donkey if you want to:
* [Quickly build your own self driving RC car.](https://docs.google.com/document/d/11IPqZcDcLTd2mtYaR5ONpDxFgL9Y1nMNTDvEarST8Wk/edit#heading=h.rqp8wbm837hn) (~$200 + 4hrs).
* Use existing autopilots to drive your car.
* Use community datasets to create, improve and test autopilots that other people can use.  


#### Features:
* Data logging of image, steering angle, & throttle outputs. 
* Wifi car controls (a virtual joystic).
* Community contributed driving data and autopilots.
* Hardware CAD designs for optional upgrades.


### Drive your car
Once you have built your car you can use it like this.

1. Start the default pilot server. `python scripts/serve.py`
2. Start your car and connect it to the pilot server. `python scripts/drive_pi.py  --remote http://<your_pilot_server_ip>:8887`
3. Go to `<your_pilot_server_ip>:8887` on your phone or computer to start driving your car. 

 





