"""
Scripts to drive a donkey car remotely

Usage:
    remote_cam_view.py --name=<robot_name>


Options:
    -h --help     Show this screen.
"""
import os
import time
import math
from docopt import docopt
import donkeycar as dk

from donkeycar.parts.cv import CvImageView, ImgBGR2RGB, ImgRGB2BGR, ImageScale, ImgWriter, ArrowKeyboardControls
from donkeycar.parts.salient import SalientVis
from donkeycar.parts.network import MQTTValuePub, MQTTValueSub
from donkeycar.parts.transform import Lambda
from donkeycar.parts.image import JpgToImgArr

V = dk.vehicle.Vehicle()
args = docopt(__doc__)
print(args)

V.add(MQTTValueSub(name="donkey/%s/camera" % args["--name"]), outputs=["jpg"])
V.add(JpgToImgArr(), inputs=["jpg"], outputs=["img_arr"]) 
V.add(ImgBGR2RGB(), inputs=["img_arr"], outputs=["rgb"])
V.add(ImageScale(4.0), inputs=["rgb"], outputs=["lg_img"])
V.add(CvImageView(), inputs=["lg_img"])

V.add(ArrowKeyboardControls(), outputs=["control"])
V.add(MQTTValuePub(name="donkey/%s/controls" % args["--name"]), inputs=["control"])


V.start(rate_hz=20)

