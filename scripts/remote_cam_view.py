"""
Scripts to drive a donkey 2 car

Usage:
    remote_cam_view.py [--ip="localhost"]


Options:
    -h --help     Show this screen.
"""
import os
import time
import math
from docopt import docopt
import donkeycar as dk

from donkeycar.parts.cv import CvImageView, ImgBGR2RGB, ImgRGB2BGR, ImageScale, ImgWriter
from donkeycar.parts.salient import SalientVis
from donkeycar.parts.network import ZMQValueSub, UDPValueSub, TCPClientValue
from donkeycar.parts.transform import Lambda
from donkeycar.parts.image import JpgToImgArr

V = dk.vehicle.Vehicle()
args = docopt(__doc__)
cfg = dk.load_config("./config.py")

ip = args['--ip']

V.add(TCPClientValue(name="camera", host=ip), outputs=["jpg"])
V.add(JpgToImgArr(), inputs=["jpg"], outputs=["img_arr"]) 
V.add(ImgBGR2RGB(), inputs=["img_arr"], outputs=["rgb"])
V.add(ImageScale(4.0), inputs=["rgb"], outputs=["lg_img"])
V.add(CvImageView(), inputs=["lg_img"])

V.start(rate_hz=20)

