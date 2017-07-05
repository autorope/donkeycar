# About Donkey Parts

Parts are the modular components of a vehicle that are run in sequence in the
drive loop. These include ...
* Sensors - Cameras, Lidar, Odometers, GPS ...
* Actuators - Motor Controllers
* Pilots - Lane Detectors, Behavioral Cloning models, ...
* Controllers - Web based or bluetooth.
* Stores - Tub, or a way to save data. 


All Donkey Parts have a number of methods in common.
* `part.run()` : function used to run the part
* `part.run_threaded(` : drive loop function run if part is threaded.
* `part.update()` : threaded function  
