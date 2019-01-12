
import os
import time
import math
from docopt import docopt
import donkeycar as dk

from donkeycar.parts.cv import CvImageView
from donkeycar.parts.graph import Graph
from donkeycar.parts.network import ZMQValueSub
from donkeycar.parts.transform import Lambda

V = dk.vehicle.Vehicle()
ip = "localhost"
w = 640
h = 480
d = 3

def condition_values(obj):
    if obj is None:
        return None
    '''
    This expects a tuple of 4 values.
    The first value is time (x), and the rest are y values
    from -2, +2
    This will work with the network publisher test:
    python ~/projects/donkey_tkramer/donkeycar/parts/network.py
    '''

    vals = obj[1:]
    x = round(obj[0] * 30.0)
    ret = []

    i = 0
    for val in vals:
        coord = (x, val * (h / 4.) + (h / 2.))
        color = [0, 0, 0]
        color[i] = 1
        i += 1
        ret.append( (coord, color) )

    #a solid white center line.
    coord = (x, h / 2.0)
    color = (1.0, 1.0, 1.0)
    ret.append( (coord, color) )

    return ret

l = Lambda(condition_values)

V.add(ZMQValueSub(name="test", ip=ip), outputs=["obj"])
V.add(l, inputs=["obj"], outputs=["values"])
V.add(Graph(res=(h, w, d)), inputs=["values"], outputs=["graph/img"])
V.add(CvImageView(), inputs=["graph/img"])

V.start(rate_hz=10)
