import sys
import os
import time
from threading import Thread
import zmq
import cv2
import numpy
import donkeycar as dk
from donkeycar.utils import binary_to_img, img_to_arr

class ZMQValueSub(object):
    '''
    Use Zero Message Queue (zmq) to subscribe to value messages from a remote publisher
    '''
    def __init__(self, name, ip, port = 5562, hwm=1, return_last=True):
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.set_hwm(hwm)
        self.socket.connect("tcp://%s:%d" % (ip, port))
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.name = name
        self.return_last = return_last
        self.last = None

    def run(self):
        '''
        poll socket for input. returns None when nothing was recieved
        otherwize returns packet data
        '''
        try:
            z = self.socket.recv(flags=zmq.NOBLOCK)
        except zmq.Again as e:
            if self.return_last:
                return self.last
            return None

        #if self.name == obj['name']:
        #    self.last = obj['val'] 
        #    return obj['val']
        self.last = z
        return z

        if self.return_last:
            return self.last
        return None

    def shutdown(self):
        self.socket.close()
        context = zmq.Context()
        context.destroy()


class JoyStickPub(object):
    '''
    Use Zero Message Queue (zmq) to publish the control messages from a local joystick
    '''
    def __init__(self, controller_type, ip, port = 5559, dev_fn='/dev/input/js0'):
        import zmq
        self.dev_fn = dev_fn
        #self.js = LogitechJoystick(self.dev_fn)
        print("controller type: ", controller_type)
        if controller_type  == "ps3":
            from donkeycar.parts.controller import PS3Joystick
            self.js = PS3Joystick(self.dev_fn)
        elif controller_type == "ps4":
            from donkeycar.parts.controller import PS4Joystick
            self.js = PS4Joystick(self.dev_fn)
        elif controller_type == "nimbus":
            from donkeycar.parts.controller import Nimbus
            self.js = Nimbus(self.dev_fn)
        elif controller_type == "xbox":
            from donkeycar.parts.controller import XboxOneJoystick
            self.js = XboxOneJoystick(self.dev_fn)
        elif controller_type == "wiiu":
            from donkeycar.parts.controller import WiiU
            self.js = WiiU(self.dev_fn)
        elif controller_type == "F710":
            from donkeycar.parts.controller import LogitechJoystick
            self.js = LogitechJoystick(self.dev_fn)
        elif controller_type == "rc3":
            from donkeycar.parts.controller import RC3ChanJoystick
            self.js = RC3ChanJoystick(self.dev_fn)
        else:
            raise("Unknown controller type: " + controller_type)

        self.js.init()
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.connect("tcp://%s:%d" % (ip, port))

    def run(self):
        while True:
            button, button_state, axis, axis_val = self.js.poll()
            if axis is not None or button is not None:
                if button is None:
                    button  = "0"
                    button_state = 0
                if axis is None:
                    axis = "0"
                    axis_val = 0
                message_data = (button, button_state, axis, axis_val)
                self.socket.send_string( "%s %d %s %f" % message_data)
                #print("SENT", message_data)


def donkey_camera(ip_address, port_no, title):
    print("receiving camera data...")
    s = ZMQValueSub("camera", ip=ip_address, port=port_no, hwm=1)
    while True:
        jpg = s.run()
        #print(res)
        if jpg != None:
            #print("got:", len(jpg))
            image = binary_to_img(jpg)
            img_arr = img_to_arr(image)
            scale = 5
            height = img_arr.shape[0] * scale
            width = img_arr.shape[1] * scale 
            resize_img = cv2.resize(img_arr, (width, height))
            cv2.imshow(title, resize_img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

def donkey_joystick(ip_address, port_no):
    cfg = dk.load_config()
    p = JoyStickPub(cfg.CONTROLLER_TYPE, ip_address, port_no)
    p.run()


if __name__ == "__main__":
    args = sys.argv
    if len(args) >= 2:
        try:
            print("*** start donkey controller")
            print("zmq proxy: ", args[1])
            #
            thread_js   = Thread(target=donkey_joystick, args=(args[1], 5559))
            thread_cam1 = Thread(target=donkey_camera, args=(args[1], 5562, "driver's view"))
            #thread_cam2 = Thread(target=donkey_camera, args=(args[1], 5564, "bird's eyes view"))

            thread_js.start()
            thread_cam1.start()
            #thread_cam2.start()
        except KeyboardInterrupt:
            print("keyboard Interrupt")
    else:
        print("Argument are too short")
