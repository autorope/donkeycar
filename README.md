# The Donkey 
A small utilitarian self driving vehicle. 

* Project goal: The the sidewalk self driving vehicle (auto). 

### Build your own.
Here are [detailed instructions](get_started.md) and part lists to build your own car. 


## How to use.

### Train a route
 (control in browser at <localhost or ip_address>:8889)

Start the car 
```bash
python manage.py record --webcontrol
```


### Let the donkey drive itself. 

train predictors from recorded data

```
python manage.py train --indir  <indir path>
```


### Driving




### Other Stuff 
* Find your Raspberry Pi:
	'''
    sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'
    '''


TODO: 

- [ ] Threadsafe image capture (for webserver + recorder)
- [ ] Update vehicle to drive given manual input.
- [ ] Try loading tensor flow on Raspberry Pi
- [ ] Train Convolution network from numpy arrays

Email Adam, Keven and Jeff about the Jan 22nd Race 


