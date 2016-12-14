## Donkey (or Poney) 
A RC car controled by a Raspbery Pi. 

Project goal: The the sidewalk self driving vehicle (auto). 

### Use

clone repo & create virtual env

```
git clone git@github.com:wroscoe/donkey.git
cd donkey
virtualenv env -p python3
source env/bin/activate
```


drive (control in browser at <localhost or ip_address>:8889)

```bash
python manage.py record  (manual mode)
python manage.py auto 	 (autopilot mode)
```

train predictors from recorded data

```
python manage.py train --indir  <indir path>
```


### Driving




### Other Stuff 
* Find your Raspberry Pi:
    sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'



TODO: 

- [ ] Threadsafe image capture (for webserver + recorder)
- [ ] Update vehicle to drive given manual input.
- [ ] Try loading tensor flow on Raspberry Pi
- [ ] Train Convolution network from numpy arrays

Email Adam, Keven and Jeff about the Jan 22nd Race 


