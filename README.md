# Donkey: a self driving library for small scale DIY vehicles. 

Donkey is minimalist and modular self driving library written in Python. It is developed with a focus on being easily accessable and allowing fast experimentation. 

Use Donkey if you want to:
* quickly [build your own self driving RC Car]((docs/get_started.md) with a Raspbery Pi.
* test out your self driving idea 


Guiding Principles
* **Modularity**: A self driving system is composed of standalone, independently configurable modules that can be connected modules.

* **Minimalism**: Each component should be kept short (<100 lines of code). Each peice of code should be transparent apon first reading. No black magic, it slows the speed of innovation. 

* **Extensiblity**: New components should be simple to create by following a template. 

* **Python**: Keep it simple. 

*** These guidelines are nearly copied from Keras because they are so good *** 



### How to use.
After you've 

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




