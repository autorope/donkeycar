# FAQ
---------

### What types of RC cars work with the donkey platform?
Most hobby grade RC cars will work fine with the electronics but you'll need to make your own baseplate and camera
holder. To make sure the car will work with Donkey check theses things.

* it has a separate ESC and reciever. Some of the cheaper cars have these combined so it would require soldering to
connect the Donkey motor controller to the ESC.
* The ESC uses three-wire connectors. This will make it easy to just plug into the Donkey hardware.
* Brushed motors are easier because they can go slower but brushless motors can work as well.

For more information, see [Roll Your Own](/roll_your_own.md).

### What car can I use if I'm not in the USA?
The easiest thing to do would be to take your parts down to your local RC / hobby shop and check that the car you want
works with the parts. Here are some parts people have said work in other countries.

* Austrailia: [KAOS](https://www.hobbywarehouse.com.au/hsp-94186-18694k-kaos-blue-rc-truck.html) (functionally equivalent to the Exceed Magnet)
* China: [HSP 94186](https://item.taobao.com/item.htm?spm=a1z02.1.2016030118.d2016038.314a2de7XhDszO&id=27037536775&scm=1007.10157.81291.100200300000000&pvid=dd956496-2837-41c8-be44-ecbcf48f1eac) (functionally equivalent to the Exceed Magnet)
* Add your country to this list (click edit this in top left corner)


### How can I make my own track?
You can use tape, ribbon or even rope. The most popular tracks are 4ft wide and have 2in white borders with a dashed
yellow center line. The Oakland track is about 70 feet around the center line. Key race characteristics include:
* straightaways.
* left and right turns
* hairpin turn
* start/finish line.


### Will Donkey Work on different hardware?
Yes. It's all python so you can run it on any system. Usually the hard part of porting Donkey will be getting the hardware working.
Here are a couple systems that people have tried or talked about.

* NVIDA TX2 - This was implemented with a webcam and used a teensy to controll the motor/servos. I2c control of PCA9685 works as well.

* Pi-Zero - Yes, Try following the steps for the PiB/B+. They should work for the PiZero.


---
## After a reboot, I don't see the (donkey) in front of the prompt, and I get python errors when I run.
1. If you used this disc setup guide above, you used conda to manage your virtual environment. You need to activate the donkey conda environment with:
    ```
    conda activate donkey
    ```
2. optionally you can add that line to the last line of your ~/.bashrc to have it active each time you login.

----
## How to get latest Donkey source
1. When donkey has changed you can get the latest source. You've installed it directly from the github repo, so getting latest is easy:
     ```
    cd donkeycar
    git pull origin master
    donkey createcar --path ~/mycar --overwrite
    ```

