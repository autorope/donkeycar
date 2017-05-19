# Donkey: a self driving library and control platform for small scale DIY vehicles. 

Donkey is minimalist and modular self driving library written in Python. It is developed for hobbiests with a focus on allowing fast experimentation and easy community contributions.  

###[Build a Donkey Car.](http://www.donkeycar.com) 
It costs ~$200  and takes 2hrs to build one. Almost all parts can be ordered on amazon. 

#### Use Donkey if you want to:
* Make an RC car drive its self.
* Compete in self driving races like [DIY Robocars](diyrobocars.com)
* Use existing autopilots to drive your car.
* Use community datasets to create, improve and test autopilots that other people can use.  


#### Features:
* Data logging of image, steering angle, & throttle outputs. 
* Wifi car controls (a virtual joystic).
* Community contributed driving data and autopilots.
* Hardware CAD designs for optional upgrades.


### Drive your car
Once you have built your car and it's connected to the same wifi as your computer.

1. Open a terminal and clone the donkey repo: `git clone https://github.com/wroscoe/donkey`
2. Start the default pilot server using docker: `bash start-server.py`
3. Open a new terminal and find your car's Raspberry Pi's IP address: `python scripts/find_car.py` 
4. SSH to your car's Raspberry Pi: `ssh pi@<your pi's ip address>` (default password = raspberry) 
5. Start your car's driver loop: `python scripts/drive.py  --remote http://<your computers ip address>:8887`
6. Turn on your car.
7. Go to `<your_pilot_server_ip>:8887` on your phone or computer to start driving your car. 

 





