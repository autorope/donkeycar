# How to Build a Donkey V2

&nbsp;

* [Overview](build_hardware.md#overview)
* [Parts Needed](build_hardware.md#parts-needed)
* [Hardware:](build_hardware.md#hardware)
    * [Step 1: Print Parts](build_hardware.md#step-1-print-parts)
    * [Step 2: Clean up parts](build_hardware.md#step-2-clean-up-parts)
    * [Step 3: Assemble Top plate and Roll Cage](build_hardware.md#step-3-assemble-top-plate-and-roll-cage)
    * [Step 4: Connect Servo Shield to Raspberry Pi](build_hardware.md#step-4-connect-servo-shield-to-raspberry-pi)
    * [Step 5: Attach Raspberry Pi to 3D Printed bottom plate](build_hardware.md#step-5-attach-raspberry-pi-to-3d-printed-bottom-plate)
    * [Step 6: Attach Camera](build_hardware.md#step-6-attach-camera)
    * [Step 7: Put it all together](build_hardware.md#step-7-put-it-all-together)
 * [Software](install_software.md)

&nbsp;

## Overview

These same instructions can be found in this [Make Magazine article](https://makezine.com/projects/build-autonomous-rc-car-raspberry-pi/). The software has been updated since the article was published.  The latest version of the software installation instructions are maintained in the [software instructions](install_software.md) section.   Be sure to follow those instructions after you've built your car.

There are alternate cars to the Magnet car below, find them here: [alternate cars](supported_cars.md)

![donkey](../assets/build_hardware/donkey.PNG)

&nbsp;

## Parts Needed:

| Part Description                                                                    | Link                                                                                  | Approximate Cost |
|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|------------------|
| Magnet Car                                                                          | [Blue](https://www.amazon.com/gp/product/9269803775/?tag=donkeycar-20), [Red](http://amzn.to/2EIC1CF)                                         | $92              |
| M2x6 screws (4)                                                                     | [mcmaster.com/#91292a831/=177k4rp](https://www.mcmaster.com/#91292a831/=177k4rp)                                          | $6.38 *          |
| M2.5x12 screws (8)                                                                  | [mcmaster.com/#91292a016/=177k574](https://www.mcmaster.com/#91292a016/=177k574)                                          | $4.80 *          |
| M2.5 nuts (8)                                                                       | [mcmaster.com/#91828a113/=177k7ex](https://www.mcmaster.com/#91828a113/=177k7ex)                                          | $5.64 *          |
| M2.5 washers (8)                                                                    | [mcmaster.com/#93475a196/=177k7x6](https://www.mcmaster.com/#93475a196/=177k7x6)                                          | $1.58 *          |
| USB Battery with microUSB cable (any battery capable of 2A 5V output is sufficient) | [amazon.com/gp/product/B00P7N0320](https://www.amazon.com/gp/product/B00P7N0320?tag=donkeycar-20)                                          | $17              |
| Raspberry Pi 3                                                                      | [amazon.com/gp/product/B01CD5VC92](https://www.amazon.com/gp/product/B01CD5VC92?tag=donkeycar-20)                                          | $38              |
| MicroSD Card (many will work, I like this one because it boots quickly)             | [amazon.com/gp/product/B01HU3Q6F2](https://www.amazon.com/gp/product/B01HU3Q6F2?tag=donkeycar-20)                                         | $18.99           |
| Wide Angle Raspberry Pi Camera                                                      | [amazon.com/gp/product/B00N1YJKFS](https://www.amazon.com/gp/product/B00N1YJKFS?tag=donkeycar-20)                                         | $25              |
| Female to Female Jumper Wire                                                        | [amazon.com/gp/product/B010L30SE8](https://www.amazon.com/gp/product/B010L30SE8?tag=donkeycar-20)                                          | $7 *             |
| Servo Driver PCA 9685                                                               | [amazon.com/gp/product/B014KTSMLA](https://www.amazon.com/gp/product/B014KTSMLA?tag=donkeycar-20)                                          | $12 **           |
| 3D Printed roll cage and top plate.                                                 |  STL Files: [thingiverse.com/thing:2260575](http://www.thingiverse.com/thing:2260575) Purchase: [DonkeyCar Store](https://squareup.com/store/donkeycar) | $45 ***                |



*These components come in minimum quantities much higher than is necessary for a vehicle.  If you get with friends to build several the total cost of the car will be $20 cheaper.  

**This component can be purchased from Ali Express for ~2 if you can wait the 15-45 days for shipping.

***This is a maker project and it is always best to print the part, but if you don't have access to a printer, Try the DonkeyCar store where one of the original donkey team members will print one for you at a fraction of the cost of Shapeways.

&nbsp;


### Optional Upgrades
* **LiPo Battery and Accessories:** LiPo batteries have significantly better energy density and have a better dropoff curve.  See below (courtesy of Traxxas).

![donkey](../assets/build_hardware/traxxas.PNG)

| Part Description                                      | Link                                                              | Approximate Cost |
|-------------------------------------------------------|-------------------------------------------------------------------|------------------|
| LiPo Battery                                          | [hobbyking.com/en_us/turnigy-1800mah-2s-20c-lipo-pack.html](https://hobbyking.com/en_us/turnigy-1800mah-2s-20c-lipo-pack.html) | $8.94            |
| Lipo Charger (takes 1hr to charge the above battery)  | [amazon.com/gp/product/B00XU4ZR06](https://www.amazon.com/gp/product/B00XU4ZR06?tag=donkeycar-20)                                               | $13              |
| Lipo Battery Case (to prevent damage if they explode) | [amazon.com/gp/product/B00T01LLP8](https://www.amazon.com/gp/product/B00T01LLP8?tag=donkeycar-20)                                               | $8               |



&nbsp;

## Hardware
### Step 1: Print Parts
If you do not have a 3D Printer, you can order parts from Adam's [DonkeyCar Store](https://squareup.com/store/donkeycar) [Shapeways](https://www.shapeways.com/) or [3dHubs](https://www.3dhubs.com/).  One thing to note, if you buy from the Donkeycar store, all hardware is included which saves about $20.

I printed parts in black PLA, with .3mm layer height with a .5mm nozzle and no supports.  The top roll bar is designed to be printed upside down.  

&nbsp;
### Step 2: Clean up parts
Almost all 3D Printed parts will need clean up.  Re-drill holes, and clean up excess plastic.

![donkey](../assets/build_hardware/2a.PNG)

In particular, clean up the slots in the side of the roll bar, as shown in the picture below:

![donkey](../assets/build_hardware/2b.PNG)


&nbsp;
### Step 3: Assemble Top plate and Roll Cage
Slide the nut into the slot in the side of the roll cage.  This is not particularly easy.  You may need to clean out the hole again and use a small screwdriver to push the screw in such that it lines up with the hole in the bottom of the roll cage.

![donkey](../assets/build_hardware/3a.PNG)


Once you have slid the nut in, you can attach the bottom plate.  Once again, this may be tricky.  I use the small screwdriver to push against the nut to keep it from spinning in the slot.  Good news: you should never have to do this again.

![donkey](../assets/build_hardware/3b.PNG)

&nbsp;
### Step 4: Connect Servo Shield to Raspberry Pi.
You could do this after attaching the Raspberry Pi to the bottom plate, I just think it is easier to see the parts when they are laying on the workbench.  Connect the parts as you see below:

![donkey](../assets/build_hardware/4a.PNG)

For reference, below is the Raspberry Pi Pinout for reference.  You will notice we connect to 3.3v, the two I2C pins (SDA and SCL) and ground:

![donkey](../assets/build_hardware/4b.PNG)

&nbsp;
### Step 5: Attach Raspberry Pi to 3D Printed bottom plate.  
Before you start, now is a good time to insert the already flashed SD card and bench test the electronics.  Once that is done, attaching the Raspberry Pi and Servo is as simple as running screws through the board into the screw bosses on the top plate.  The M2.5x12mm screws should be the perfect length to go through the board, the plastic and still have room for a washer.  The “cap” part of the screw should be facing up and the nut should be on the bottom of the top plate.  The ethernet and USB ports should face forward.  This is important as it gives you access to the SD card and makes the camera ribbon cable line up properly.

Attach the USB battery to the underside of the printed bottom plate using cable ties or velcro.

![donkey](../assets/build_hardware/5ab.PNG)


&nbsp;
### Step 6: Attach Camera
Attaching the camera is a little tricky, the M2 screws can be screwed into the plastic but it is a little hard.  I recommend drilling the holes out with a 1.5mm bit (1/16th bit in Imperial land) then pre threading them with the screws before putting the camera on.  It is only necessary to put two screws in.  Before using the car, remove the plastic film from the camera lens.

![donkey](../assets/build_hardware/6a.PNG)


It is easy to put the camera cable in the wrong way so look at these photos and make sure the cable is put in properly.  There are loads of tutorials on youtube if you are not used to this.

![donkey](../assets/build_hardware/6b.PNG)


&nbsp;
### Step 7: Put it all together
The final steps are straightforward.  First attach the roll bar assembly to the car.  This is done using the same pins that came with the vehicle.  

![donkey](../assets/build_hardware/7a.PNG)

Second run the servo cables up to the car.  The throttle cable runs to channel 0 on the servo controller and steering is channel 1.

![donkey](../assets/build_hardware/7b.PNG)


Now you are done with the hardware!!



&nbsp;
## Software
Congrats!  Now to get your get your car moving, see the [software instructions](install_software.md) section.

![donkey](../assets/build_hardware/donkey2.PNG)


> We are a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for us to earn fees by linking to Amazon.com and affiliated sites.
