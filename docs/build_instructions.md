# Build a donkey vehicle. 


The standard hardware build instructions can be found in this 
[google doc](https://docs.google.com/document/d/11IPqZcDcLTd2mtYaR5ONpDxFgL9Y1nMNTDvEarST8Wk/edit#heading=h.ayg28mpf8hvb).


Once you have the car built and the Raspbery Pi running with the given
disk image follow these steps to start running the latest version of Donkey. 

On the Pi pull the most recent version.  
```
git fetch origin dev
get checkout dev
```

### Calibrate your vehicle.
The goal of calibrating your vehicle is to make it run the same as other vehicles
when given the same `angle` and `throttle` values. For example if you give the
car an angle=0 and throttle=0 the wheels should point straight and the 
vehicle should not move.

Assuming you've built the Donkey2 or your car uses the same motor controller 
you can run `python scripts/calibrate.py` to find the right PWM settings for 
your car. 

Enter the PWM values determined during your calibration into the 


### Drive the car.

** put your car in a box or on blocks to avoid it running away **

After you've updated the script you use to drive your car with the correct 
PWM settings then you can run the script that will start your vehicles 
drive loop. 


```
python examples/donkey2.py
```




4. Run the drive script 