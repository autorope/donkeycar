# Robocar Controller

Robocar Controller is a mobile app designed to provide a “commandless” user experience to get started with the Donkey Car. 

![cover](../assets/mobile_app/cover.png)

## Features
- Commandless experience - No SSH or text editor
- Built-in Hotspot 
- Search vehicle on the network
- Real-time Calibration
- Virtual joystick
- Visualize the data
- Drive Summary
- Free GPU training
- Autopilot
- Advanced configuration
- Battery level

## Requirements
- A Donkey Car with Pi 4B (Jetson Nano is not yet supported)
- A Mobile phone with iOS or Android

## Quickstart Guide
Please refer to the <a href="https://medium.com/robocar-store/robocar-controller-quick-start-guide-bdf8cb16d7ce?source=friends_link&sk=8f21a5792f81a1d340abe9433d78cf5b" target="_blank">quick start guide here</a>.


## Features Details
### Built-in Hotspot 
The car will become a hotspot when there is no known Wifi network to connect. After connecting your phone to this hotspot, you can use the app to configure the car to join the Wifi network you want. 

### Search vehicle on the network
Once your car connects to the same network as your phone, the app will scan the whole network to discover it. The app will also show you the IP address of the car in case you want to connect to it via SSH.

![Search Vehicle](../assets/mobile_app/search-vehicle.png)

### Real-time Calibration
Sometimes it is quite annoying if the car goes too fast or does not run in a straight line. The calibration UI assists you to find the right settings so that your car could be properly calibrated. With the enhanced calibration function, the change will take place in real time and you could observe the change immediately.

![Real-time calibration](../assets/mobile_app/calibration.png)

### Virtual Joystick
The virtual joystick offers a quick way to test drive the car if you don't have a physical gamepad controller. It also streams the video captured from the camera in real time. You can just look at the screen and start driving.

![Drive UI](../assets/mobile_app/drive-ui.gif)


### Drive Summary
The app presents a drive summary with histogram, the size and the number of images you have collected. The histogram is generated automatically by calling the ```tubhist``` function in the Donkey car software. 

![Drive summary](../assets/mobile_app/drive-summary.png)

### Visualize the data 
The app shows all the data(tubs) and the metadata you have collected on the Pi. The metadata includes number of images, size of the tub, the resolutions, the histogram and the location. The app will make use of the donkey makemovie command to generate a video so you can review how the data look like.

![Data](../assets/mobile_app/data.png)

### Free GPU Training
Free GPU training is available to user who use the app. You can train a model by selecting the data(tubs) you wish to train. The data will be uploaded to our server to start the training process. Once the training is completed, the app will show you the training loss and accuracy graph. At the same time, the app will download the model to your car and you can test the model right away.

Note: We keep the data and models for a period of time. After that, we will delete it from our storage. 

![Train](../assets/mobile_app/train.png)

#### More on Free GPU Training

We are using AWS [g4dn.xlarge](https://aws.amazon.com/ec2/instance-types/g4/) instance to train the model. It feautres [NVIDIA T4 GPU](https://www.nvidia.com/en-us/data-center/tesla-t4/) and up to 16GB GPU memory. Increase the batch size to 256 or more to fully utilize the powerful GPU.

#### Limitation
N.B.: To protect our equipment from being abused, we have the following rules to use the training service.

- Each training is limited to a maximum of 15 minutes. The training job will timeout if it last more than 15 minutes
- Each device could train 5 times per 24 hours.
- Max data size is 100MB per training

### Autopilot

The app will list all models inside the Pi, no matter it is generated from the training function or just a model copied to the Pi. You can start the autopilot mode using a similar UI as the Drive UI.

![Autopilot](../assets/mobile_app/autopilot.gif)

### Advanced configuration
The Doneky car software comes with a vast of configuration that you can experiment. We have included some of the popular options that you may want to change.

- Camera size 
- Training configuration 
- Drive train settings

![Advanced configuration](../assets/mobile_app/advanced-configuration.png)



### Battery level

If you are using MM1, the app shows you the current battery level in percentage. We have also added an OS tweak that if battery level fall below 7V, the system will shutdown automatically.



## Upcoming features
- Salient visualization
- Auto throttle compensation based on battery level
- Transfer learning 



## Report a problem
If you encountered a problem, please file an issue on [this github project](https://github.com/robocarstore/donkeycar_controller).



## FAQ
- Why the app is called Robocar Controller instead of Donkeycar Controller?

We would love to call the app Donkeycar Controller but Apple does not allow us to do so. We are working with Adam to submit a proof to Apple that we can use the Donkeycar trademark in our app. In the meanwhile, we will be using the name Robocar Controller.



## Commercial Usage
This app is developed by [Robocar Store](https://www.robocarstore.com). If you plan to use this app to make money, please follow the [Donkey Car guideline](https://www.donkeycar.com/make-money.html) and send an email to [Robocar Store](mailto:sales@robocarstore.com).