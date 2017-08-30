# Train an autopilot with Keras

Now that you're able to drive your car reliably you can use Keras to train a
neural network to drive like you. Here are the steps.

## Collect Data

Make sure you collect good data. 

1. Practice driving around the track a couple times without recording data.
2. When you're confident you can drive 10 laps without mistake press `Start Recording`
3. If you crash or run off the track press Stop Car imediatly to stop recording. 
A little bad data won't affect your autopilot. 
4. After you've collected 10-20 laps of good data (5-20k images) you can stop 
your car with `Ctrl-c` in the ssh session for your car.
5. The data you've collected is in the data folder in the most recent tub folder.


## Transfer data from your car to you computer. 

Since the Raspberry Pi is not very powerful we need to transfer the data
to our computer to train. 

In a new terminal session on your comptuer use rsync to copy your cars 
folder. 
```
rsync pi@<your_pi_ip_address>:~/d2/data  ~/d2/data
```


## Train a model.
5. In the same terminal you can now run the training script on the latest tub.
```
 python ~/d2/manage.py train --model mypilot
```

6. Now you can use rsync again to move your pilot back to your car. 
```
rsync ~/d2/models pi@<your_ip_address>:~/d2/models
```

7. Now you can start your car again and pass it your model to drive.
```
python ~/d2/manage.py drive --model mypilot
