# Release notes
Notes to remember how to release donkey.

### Create a startup disk.

The general steps of creating a startup disk are. 
1. Make the disk perfect.
2. Create startup disk.
3. Publish image and update docs. 


Once the SD card is ready and tested take it out of the Pi and into your 
computer. Run `sudo gparted` to see the size of the disk partitions. Then resize
the partitions to be as small as possible. Right click the partition and
see the last sector of the partition. 

Then run

dd -if /def/sdb -of /




### Create a release 

Update setup.py
1. update the version in set 