# The Donkey 
A small utilitarian self driving vehicle. 

* Project goal: The the sidewalk self driving vehicle (auto). 

### Build your own.
Here are [instructions](get_started.md) and part lists to build your own car. 


## How to use.
All of these examples assume you're connected to your donkey via SSH and you've activated the virtual environment. 

### Activate the virtual environment
```
cd code/donkey
source env/bin/activate 
```

### Train a route

1. Start recording steering and images 
```bash
python manage.py record --filerecorder --webcontrol
```

2. Go to '<pi_ip_address>:8889' in your browser to control the car.

3. End training by typing `Ctrl-c` in your ssh sesion.

### Create a predictor for the route. 

Train predictors from recorded data

```
python manage.py train --indir  <indir path>
```


### Let the predictor drive the trained rout. 

```
python manage.py auto --indir  <indir path>
```
Where indir is the directory of the images used to train the predictor. 


##TODO: 

- [x] Threadsafe image capture (for webserver + recorder) 
- [ ] Update vehicle to drive given manual input. (Adam)
- [ ] Try loading tensor flow on Raspberry Pi (Will)
- [ ] Train Convolution network from numpy arrays (Will)

Email Adam, Keven and Jeff about the Jan 22nd Race 


