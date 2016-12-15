# The Donkey 
A small DIY self driving vehicle made from an RC Car and Raspbery Pi. 

>Project goal: Build a vehicle that can navigate safely around any city block without being shown the route.

### Build your own.
Here are [instructions](docs/get_started.md) and part lists to build your own car. 


## How to use.
***All of these examples assume you're connected to your donkey via SSH and you've activated the virtual environment.***


### Train a route

1. Start driving mode. 
```
python manage.py drive --session firstdrive
```

2. Go to `<pi_ip_address>:8889` in your browser to control the car.


### Create a predictor for the route. 

Train predictors from recorded data

```
python manage.py train --session firstdrive --model firstmodel
```


### Test out the self driving. 

1. Start the donkey so data is recorded in a different session and load the predictor you trained. 

```
python manage.py drive --session seconddrive --model firstmodel
```
2. Go to `<pi_ip_address>:8889` and click **Start Self Driving** button. Your dokney should now drive it's self based on what you taught it. 


##Next Steps

Try changing or creating your own predictor. 

##TODO: 

Web & Python
- [x] Threadsafe image capture (for webserver + recorder) 
- [ ] Create togle on LocalWebControler to togle autonomous mode. (Will)
- [ ] Create `manage.py serve` command to run local server to act as a remote Recorder and Predictor. (Will)
- [ ] Separate Keras Predictors so they don't need to be run on the Pi.
- [ ] Write Tests

Vehicle Control 
- [ ] Update vehicle to drive given manual input. (Adam)
- [ ] Try loading tensor flow on Raspberry Pi (Will)

Machine Learning
- [ ] Train Convolution network from numpy arrays (Will)

Refactor Worthy
- [ ] Get rid of all the global variables (GLB) 




