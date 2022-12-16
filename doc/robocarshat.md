# DIYRobocarsFr Hat

DIYRobocarsFr Hat is a daughter board (Hat) for Raspberry Pi or Nvidia Jeston Nano or any other SBC with Raspberry compatible GPIO to ease the built of autonomous small scale RC-style car like the Donkey car. You can find more about DIYRobocarsFr Hat here :
- [software](https://github.com/btrinite/robocars_hat)
- [hardware](https://github.com/btrinite/robocars_hat_hw)

#### Main changes to integrate RobocarsHat :
- new part : [robocars_hat_ctrl.py](./donkeycar/parts/robocars_hat_ctrl.py) with new Class RobocarsHatIn, which is both a part to add support for receiving throttle and steering command from an RC Receiver and also act as low level driver between raspberry pi/jetson nano and the hat (to control the serial port). The controler part is enabled by setting USE_ROBOCARSHAT_AS_CONTROLLER configuation key to True.
- updated [actuator.py](./donkeycar/parts/actuator.py) with a new Class RobocarsHat that is used to send throttle and steering orders to the hat, enabled by setting DRIVE_TRAIN_TYPE configuration key to ROBOCARSHAT.
- new set of config parameters (search ROBOCARSHAT)
- update [complete.py](./donkeycar/templates/complete.py) with instantiation of RobocarsHatIn and RobocarsHat accordingly to configuration.

Warning : for Raspberry pi 3, you have to get rid of 'miniuart' and resplace it by the true UART device known as PL011.
You will most likely lose Bluetooth. You can check [here](https://www.circuits.dk/setup-raspberry-pi-3-gpio-uart/)

#### Calibration :
PWM signal is supposed to be square signal with positive pulse duration from 1ms to 2ms
This pulse width represents the 'value' carried.
For example, talking about steering, 1ms could mean to turn to the most left, and 2ms to turn to the most right
Pulse width at 1.5ms is then the theoritical idle position for the steering. This is more os less the same for the control of throttle as long as we are talking about cat (1ms means full reverse, 1.5 means idle and 2ms means full forward).
Now, a real Tx/RX signal would not stick strictly on those values. This is why qualibration is needed.

The simple way to qualibrate :
- Make sure your remote control is on idle position
- Make sure your car is on a stand, wheels being free to move in case of
- Connect the Rx Receiver to the Hat
- Connect the ESC control line to the Hat (3 Wire, neede because ESC is in charge to provide power supply to the RX Receiver)
- Power the Hat+Host
- Note the idle, minimum and maximum values reported by the Hat when actioning the remote control
- Update the following configuration items accordingly :
    - ROBOCARSHAT_PWM_IN_THROTTLE_MIN : value reported by Hat when moving remote control to the lowest throttle value
    - ROBOCARSHAT_PWM_IN_THROTTLE_IDLE : value reported by Hat when moving remote control to the default/idle throttle value
    - ROBOCARSHAT_PWM_IN_THROTTLE_MAX : value reported by Hat when moving remote control to the highest throttle value
    - ROBOCARSHAT_PWM_IN_STEERING_MIN : value reported by Hat when moving remote control to the maximum steering postion of one of the direction (the one that provides the minimum value)
    - ROBOCARSHAT_PWM_IN_STEERING_IDLE : value reported by Hat when moving remote control to the default steering postion 
    - ROBOCARSHAT_PWM_IN_STEERING_MAX : value reported by Hat when moving remote control to the maximum steering postion of the other direction (the one that provides the maximum value)

To visualize easely value reported by the Hat, 2 possibilities according to the firmware you use :
- With ROS :
    Dump incoming messages related to radio channes :  

    ``rostopic echo /radio_channels`` 

    Messages contains an array of 4 ints : 

    ``
        ...
        data: [xxxx yyyy, aaaa, bbbb]
    ``
    
- With Simple Serial Protocol (Text Protocol) :  
    Dump incoming messages : 

    `` stty -F /dev/serial0 1000000 raw `` 

    `` cat /dev/serial0 | grep "^1," `` 
 
    Messages like ``1,xxxx,yyyy,aaaa,bbbb`` are the Radio channel messages

Throttle is the first value out of four (xxxx) 
Steering is the second value out of four (yyyy)

If you see only 1500 as value, it means that Rx Receiver PWM signal has not been detected (you should see also status LED blinking either RED or BLUE).

