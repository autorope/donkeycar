### Connect to your car via ssh.

All these instructions assume your working on a unix based OS (Linux/iOS)

On a terminal in your computer install donkeycar:
```
pip install -U donkeycar
```

Find the ipaddress if your car.
```donkey findcar```

Then SSH into your car's Raspberry Pi.
```
ssh pi@<your pi's ip address>
```



### Create a drive script on your car.

Ugrade the install of donkeycar. 
```
pip uninstall donkeycar
pip install donkeycar
```

Use a template to create a car folder structure.
```
donkey createcar --path ~/d2 --template donkey2
```

This created a new folder whith a script to start your car and folders to save
data and models.



### Start your car.
 
> *** Put your car in a safe place where the wheels are off the ground *** This
is the step were the car can take off. 

Open your car's folder and start our car. 
```
cd ~/d2
python manage.py drive
```

This script will start the drive loop in your car which includes a part that 
is a webserver for you to control your car. You can now controll your car
from a web browser at the url: `<your car's ip's address>:8887`
