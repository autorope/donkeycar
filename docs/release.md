# Release notes
Notes on how to release donkey.

### Create a startup disk.


1. Download the previous disk image and create the startup disk.
2. Move disk to you pi.
3. Pull the lastest donkeycar code.
4. Make your changes.
5. Move the disk back to your computer.
6. Remove your wi-fi password and change the host name to donkeypi. Delete `.gitconfig`.
7. Create the disk image from the SD card

    Run `sudo gparted` to see the size of the disk partitions. Resize the partitions
    to be as small as possible. Right click the partition to see the last sector of the partition.

    Run `sudo dd if=/dev/mmcblk0 of=~/donkey_2.5.0_pi3.img bs=512 count=<last sector> status=progress`

8. Zip the .img file and upload to Dropbox.
9. Update the link in the instructions.

### Create a release

1. Run the tests on computer and pi. `pytest`
2. Update versions in `__init__` and `setup.py`
