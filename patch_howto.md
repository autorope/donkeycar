# how to install this fork over your install

``` 
pip uninstall donkeycar
git clone --depth=1 https://github.com/tawnkramer/donkey donkey_tkramer
cd donkey_tkramer
pip install -e .
```

### if you want joystick control
```
donkey createcar --template donkey2_with_joystick --path ~/d2_wj
```
### if you want webui control
```
donkey createcar --template donkey2 --path ~/d2
```

