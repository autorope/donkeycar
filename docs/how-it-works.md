## Notes on how the software works - by @adrianco
* Reading the code for the first time, there are likely to be some errors here

----
## Run server on the EC2 instance - scripts/serve.py
* Web server for user interface
* Serves multiple vehicles and pilots from a single instance
* Pilots can be users or autopilots
* Collects sessions for training
### remotes.py - donkey.remotes.DonkeyPilotApplication
* tornado web application
#### home page
* add screen shot of home page here
#### vehicles
* VehicleListView - List of vehicles connected 
* VehicleView - Control page for selected vehicle
#### sessions - captured 160x120 pixel 4KB images for training
* SessionListView - show all the session folders
* SessionView - show all the images in a session and delete selected
* SessionImageView - returns jpeg images from a session folder
#### pilots
* PilotListView - show list of pilot options
#### api/vehicles
* VehicleAPI - change the pilot
* DriveAPI - receive POST requests from VehicleView to control steering and throttle
* VideoAPI - serves a MJPEG of images from the vehicle updated at 5fps
* ControlAPI - Receive POST from vehicle and return steering/throttle from a pilot
* Logs - REMOTE angle: throttle: drive_mode:

---
## Run on the Raspberry Pi3 on the car - scripts/drive.py
* started with URL to server as argument
* config from vehicle.ini - there are other files for differential cars and specific models
* trained model is default.h5 specified in vehicle.ini, about 500KB
* set up actuators to control steering and throttle
* mixers.AckermanSteeringMixer - blend steering and throttle
* sensors.PiVideoStream - setup image capture from camera
* remotes.RemoteClient - setup remote hosts
* pilots.KerasCategorical - choose and setup local Keras pilot
* vehicles.BaseVehicle - create a car
* start the car

### remotes.py - donkey.remotes.DonkeyPilotApplication
* client code for talking to the EC2 instance
#### RemoteClient - send post requests to the server
* update - loop to request the server, delay 20ms
* decide - post sensor data to server and get angle/throttle back
* connection failures retry after 3s
* timeouts after 250ms, reduce throttle to 80%

### mixers.py - blend steering and throttle
* options for separate steering servo and for differential motor drive

### sensors.py - camera and a test fake camera only
#### PiVideoStream - initialize and wait 2s for it to warm up

### pilots.py - manage pilots, can contain one or more models to control throttle/steering
#### KerasCategorical - load the model
* keras.models.load_model - pick the right pilot
* model.predict - decide what throttle/steering to use based on an image

### vehicles.py - pull together everything to make a car
#### BaseVehicle - initialize and start the drive loop
* get timestamp
* get current frame from camera
* make remote call passing in image, angle, throttle, and time since start
* if drive_mode local - use pilot to decide angle/throttle
* if drive_mode local_angle - use pilot to decide angle only
* update actuator mixer with angle/throttle
* calculate lag to get round loop
* log CAR: angle: throttle: drive_mode: lag:
* sleep for remaining time up to 500ms 

----
## Training
### scripts/explore.py - train and test many models to find the best one
* loop and explore parameters on datasets

### scripts/sessions_to_hdf5.py - create a model containing dataset from session(s)

### scripts/simulate.py - run a fake car on the server, generate fake images

### scripts/train.py - train a keras model from simulated or recorded sessions
* batch size 128
* sessions.sessions_to_dataset - combine multiple sessions into a dataset
* datasets.split_datasets - separate training and validation data, 10% chunks
* models.categorical_model_factory - create model using nvidia_conv
* models.train_gen - steps set to number of training batches (I think?)

### models.py - create and train models
#### nvidia_conv - five convolution layers and two dense layers
#### categorical_model_factory - create model with categorical angle/continuous throttle outputs
* model.compile - loss function weights angle loss 0.9 more than throttle loss 0.1
#### train_gen - train and save the best until validation error stops improving
* model.fit_generator - default 10 steps per epoch - set by amount of data, 100 epochs

### datasets.py - datasets are images and and angle/throttle values
#### split_datasets - return three shuffled generators for train, validate and test

### sessions.py - images with angle, throttle and milliseconds since start in filename
* Example frame_01359_ttl_0.25_agl_3.4989908547067235e-18_mil_0.0.jpg
* Above has throttle at 25% and angle near zero, time not being recorded

----
## Utilities
### scripts/setup.py - create default folder, copy config file and model to be customized

### scripts/find_car.py - find your car's IP on a local network

### scripts/upload_to_S3.py - upload dataset to S3 - default bucket donkey_resources

---
## Predict server, different authors
### sdsandbox_drive.py - alternative server implementation, steering only
