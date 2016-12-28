"""Records training data and / or drives the car with tensorflow.
Usage:
    drive.py  pi [--remote=<name>] [--fake_camera=<path>]
    drive.py  pi [--remote=<name>] [--fake_camera=<path>]

Options:
  --remote=<name>   recording session name
  --fake_camera=<path>    path to pictures to use as the camera
"""

import os

from docopt import docopt
from donkey.car import Car
from donkey import cameras


# Get args.
args = docopt(__doc__)






if __name__ == '__main__':

    remote_url = args['--remote']
    img_dir = args['--fake_camera'] or None 

    try:
      import picamera
      camera = cameras.PiVideoStream() #Raspberry Pi Camera

    except ImportError:
        print("Cound not load PiCamera. Using FakeCamera for testing.")
        if img_dir is None:
            img_dir = os.path.dirname(os.path.realpath(__file__))+'/datasets/imgs/'
        camera = cameras.FakeCamera(img_dir) #For testing



    if remote_url is None:
        raise ValueError('You need to specify a remote server to drive your vehicle.')



    #Start your car
    CAR = Car(vehicle_id='mycar', 
              remote_url = remote_url)
    CAR.camera = camera

    CAR.start()
