"""
Scripts to drive a donkey 2 car

Usage:
    salient_vis_listener.py [--ip="localhost"] [--model=<model>] [--type=(linear|categorical|rnn|imu|behavior|3d|localizer)]


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
from donkeycar.parts.network import ValueSub, UDPListenBroadcast
from donkeycar.parts.transform import Lambda

V = dk.vehicle.Vehicle()
args = docopt(__doc__)
cfg = dk.load_config()

model_path = args['--model']
model_type = args['--type']
ip = args['--ip']

if model_type is None:
    model_type = "categorical"

model = dk.utils.get_model_by_type(model_type, cfg)
model.load(model_path)

V.add(ValueSub(name="camera", ip=ip, hwm=1), outputs=["img"])
#V.add(UDPListenBroadcast(name="camera"), outputs=["img"])
V.add(ImgBGR2RGB(), inputs=["img"], outputs=["img"])
V.add(SalientVis(model), inputs=["img"], outputs=["img"])
V.add(ImageScale(2.0), inputs=["img"], outputs=["img"])
V.add(CvImageView(), inputs=["img"])
#V.add(ImgWriter("test.jpg"), inputs=["img"])

V.start(rate_hz=10)

