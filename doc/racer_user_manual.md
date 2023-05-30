# Intro
This readme provides basic information on how to race a Robocars provided by Renault Digital for Vivatech 2023
To pperforma some tasks, You will need :
    - an UNIX like host (Linux, MacOS)
    - an USB token for authentication to access GCP Renault
    - have some rights in project CDP ()

# donkeycar hardware description
Donkeycar is made of :

- car chassis (Kyosho Fazer MK2 chassi kit, https://fr.kyoshoeurope.com/k34461b-kyosho-fazer-mk2-chassis-kit.html), including :
    - Steering Servocontroler
    - Electronic Speed COntroler (aka ESC)
    - Brushless Motor
    - LiPo Battery
    - 3 Channels RC Controler
    - 3 Channels RC Receiver
- 3D printed plate and camera support (depends on car body)
- Jetson Nano Single Board Controler
- Robocars Hat (https://github.com/btrinite/robocars_hat_hw)
- Luxonis USB Camera (several possible model)
- car body (Alpine/Mobilize Duo/Renault/Dacia), including addressable LEDs
- various cables

# Note on LiPo battery
- LiPo battery must be carrefuly handled. They do not support (and become dangerous) if too much discherged.
:warning: They must be disconnected when not used (both connector, main and balance)
- They must be monitored and recharged when low. Robocars Hat will blink RED is it detects low voltage on battery.
- They must never been short circuited (real risk of fire/explosion)

# install Donkey on Host
- Follow http://docs.donkeycar.com/guide/install_software/#step-1-install-software-on-host-pc
- :warning: Our Donkeycar repo is : https://github.com/roboracingleague/donkeycar.git, main branch is ```main```

# install additional repo on host :
- https://github.com/roboracingleague/robocar-gcp-trainer.git , main branch is ```master``` 
    this repo contains donkey wrapper to submit train task to GCP, and some script
- follow requirements provided in https://github.com/roboracingleague/robocar-gcp-trainer/blob/master/README.md
- install some scripts to you car directory :
```sh
$TRAINER_DIR/install.sh
```

# review donckeycar configuration
## PWN Input calibration
See [robocarshat.md](robocarshat.md), chapter [Calibration](robocarshat.md#calibration)

# Donkeycar principle and end to end steps
Donkeycar is based mainly on mimic learning.
No model is provided by default, which means that from scratch, donkeycar does'nt know how to drive.
It drives based on a CNN based nodel, which needs to be trained first.

The complet cycle is like :
- drive manually the car while recording data
- train model with collected data on host or cloud platform
- transfert resulting trained model to the car
- start the the car in auto pilot mode

Steps in details :
## Drive manually to collect dataset for training
- Power up the car, wait for the car to be connected to the Wifi
    - To power the car, you must connect the two connector from the LiPo to the Car :
        - one big connector to ESC (this is the power supply for motor and steering servo)
        - the balance connector to the one connected to the Robocars Hat (connecting this one will power the Jetson Nano)
- SSH to the car
    - generic username is ```donkey```
    - car are exposing mdsn resolved machine name, like :
    ```sh
    ssh donkey@pc92.local
    ```
- launch donkeycar for manual driving
    - typically :
    ```sh
    cd ~/car # This directory at created at install time
    python manage.py drive
    ```
- Drive manually the car using RC while recording images and driving parameters (steering and throttle order you provided)
    - when started, you should get :
        - message on console like :
        ```
            INFO:donkeycar.vehicle:Starting vehicle at 60 Hz
        ```
        - RGB LED on Robocars Hat should be BLUE FIXED

    - if configured, recording is controlled thanks to the third channel on RC controller
    - Each time 10 images are recorded, you should see message on console like :
    ```
        recorded 10 records
        recorded 20 records
        recorded 30 records
    ```
    - if previous images are not deleted, the recording will resume on-going recording instead of replacing previous one.
    To clean up previous record, and before starting donkeycar, you must :
    ```sh
        cd ~/car
        rm -r -f data/*
    ``` 
    - you will at least need around 15000 images 
- stop the Donkeycar
    - just issue ```Ctrl+C``` on the console

### Create dataset archive
- Create archive of collected data 
    - for that purpose, use the make_tub_archive.sh script as follow :
    ```sh
        ./make_tub_archive.sh
    ```
    - by default, an archive wip.tgz will be created.

## Transfert the dataset to the host
- Tranfert collected data to the host (using SCP from the Host)
    ```sh
    scp donkey@pc92.local:/home/donkey/car/wip.tgz .
    ```

## Optionaly, review and cleanup data
- review and clean the data (if mistakes was done during manual driving for example)
```
cd ~/mycar # depends on the 'car' directory name choosen at install time
./deflate_tub_archive.sh # to deflqt archive locqlly
donkey ui
```
- if you made change with donkey ui (deleted some sequence for example)m, you must rebuild the archive with :
    ```sh
        ./make_tub_archive.sh
    ```

## Upload archive to GCS Bucket
- upload the archive to your GCS bucket
    ```sh
        ./upload_tub_archive.sh
    ```

## Launch GCP based training
- Train model with this data (during that time, you can shutdown the car to preserve battery)
```sh
cd <robocar-gcp-trainer direcrory>
./submit_cloud_train.sh
```
Training task will takes from 10mins to 20 mins, depending on dataset size. Command will output progress.

## Download resulting trained model
- download resulting model to your host :
```sh
cd ~/mycar
./download_model.sh
```

## Transfert trained model to the car
- Transfert train result (weights files) to the Robocar
We only need onnx model to run it on the car
```sh
scp ~/mycar/pilot-wip.onnx donkey@pc92.local:/home/donkey/car/models
```

## Test the trained model
- Power up the car if needed, 

- ensure auto pilot is in 'local_angle' mode, review config key ROBOCARSHAT_PILOT_MODE
- adjust config key ROBOCARSHAT_LOCAL_ANGLE_FIX_THROTTLE, to match throttle used for training (check with donkey UI)

- start Donkeycar with model
```sh
python manage.py drive --type=onnx_linear --model=models/pilot-wip.onnx
```
# Manage WIFI connection

WiFi network configuration files are in :
```sh
/etc/NetworkManager/system-connections
```

If you can not access to the prompt, several options :
- connect Ethernet cable (at home)
- connect USB cable (next to Ethernet connector)) between your host and the Jetson Nano, and type in your host :
```
tio -b 115200 /dev/ttyACM0 # tty name depends on platform
```
For WINET, you must configure your IPN and Password in relevant file (usualy ```WINET```) :
```
identity=<your IPN (lowercase)>
password=<Your ARCA password>
```

You can create more file for other WiFi network, be sure file is only accessible to root

A typical file content for Home WiFi/Mobile Access Point :
```
[connection]
id=Benben
uuid=4e4ef2b5-69c6-410d-a4cb-2be204841ca3 #Be sure this ID is uniq across other configs 
type=wifi
interface-name=wlan0
permissions=

[wifi]
mac-address-blacklist=
mode=infrastructure
ssid=Benben

[wifi-security]
key-mgmt=wpa-psk
psk=<Your WiFi password>

[ipv4]
dns-search=
method=auto

[ipv6]
addr-gen-mode=stable-privacy
dns-search=
method=auto
```

# Update Donkeycar
To update donkeycar software :
```sh
cd ~/donkeycar
git pull
cd ~/car
rm manage.py
donkey createcar --path /home/donkey/car --overwrite
```

then review config change and impact myconfig.py if needed :
```sh
diff config.py ~/donkeycar/donkeycar/templates/cfg_complete.py
```