# Train an Machine Learning Autopilot with Keras

After you have built a car you want to make it drive it's self. One way that's 
show to work well is by training a neural network to replicate your actions
based on the images it sees. 

1. Start your car.
2. While driving your car around a track, press the record button in the 
web controller. This will start recording images and steering and throttle 
vallues. 
3. After you've driving the track 20-30 times, stop the car with Ctr-c in
the ssh session. 
4. In a new terminal session on your comptuer use rsync to copy your cars 
folder. 
```
rsync pi@<your_pi_ip_address>:~/d2  ~/d2
```

5. In the same terminal you can now run the training script on the latest tub.
```
 python ~/d2/manage.py train --model mypilot
```

6. Now you can use rsync again to move your pilot back to your car. 
```
rsync ~/d2 pi@<your_ip_address>:~/d2
```

7. Now you can start your car again and pass it your model to drive.
```
python ~/d2/manage.py drive --model mypilot
