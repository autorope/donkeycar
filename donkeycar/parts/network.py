import socket
import zlib, pickle
import zmq

class ZMQValuePub(object):
    '''
    Use Zero Message Queue (zmq) to publish values
    '''
    def __init__(self, name, port = 5556, hwm=10):
        context = zmq.Context()
        self.name = name
        self.socket = context.socket(zmq.PUB)
        self.socket.set_hwm(hwm)
        self.socket.bind("tcp://*:%d" % port)
    
    def run(self, values):
        packet = { "name": self.name, "val" : values }
        p = pickle.dumps(packet)
        z = zlib.compress(p)
        self.socket.send(z)

    def shutdown(self):
        print("shutting down zmq")
        #self.socket.close()
        context = zmq.Context()
        context.destroy()

class ZMQValueSub(object):
    '''
    Use Zero Message Queue (zmq) to subscribe to value messages from a remote publisher
    '''
    def __init__(self, name, ip, port = 5556, hwm=10, return_last=True):
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

        #print("got", len(z), "bytes")
        p = zlib.decompress(z)
        obj = pickle.loads(p)

        if self.name == obj['name']:
            self.last = obj['val'] 
            return obj['val']

        if self.return_last:
            return self.last
        return None

    def shutdown(self):
        self.socket.close()
        context = zmq.Context()
        context.destroy()

class UDPValuePub(object):
    '''
    Use udp to broadcast values on local network
    '''
    def __init__(self, name, port = 37021):
        self.name = name
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)    
        self.server.settimeout(0.2)
        self.server.bind(("", 44444))

    def run(self, values):
        packet = { "name": self.name, "val" : values }
        p = pickle.dumps(packet)
        z = zlib.compress(p)
        self.server.sendto(z, ('<broadcast>', self.port))

    def shutdown(self):
        self.server.close()

class UDPValueSub(object):
    '''
    Use UDP to listen for broadcase packets
    '''
    def __init__(self, name, port = 37021):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.bind(("", port))
        self.name = name
        self.last = None
        self.running = True

    def run(self):
        self.poll()
        return self.last

    def run_threaded(self):
        return self.last

    def update(self):
        while self.running:
            self.poll()

    def poll(self):
        data, addr = self.client.recvfrom(1024 * 65)
        print("got", len(data), "bytes")
        if len(data) > 0:
            p = zlib.decompress(data)
            obj = pickle.loads(p)

            if self.name == obj['name']:
                self.last = obj['val']


    def shutdown(self):
        self.running = False
        self.client.close()



class MQTTValuePub(object):
    '''
    Use MQTT to send values on network
    pip install paho-mqtt
    '''
    def __init__(self, name, broker="iot.eclipse.org"):
        from paho.mqtt.client import Client

        self.name = name
        self.message = None
        self.client = Client()
        self.client.connect(broker)
        self.client.loop_start()

    def run(self, values):
        packet = { "name": self.name, "val" : values }
        p = pickle.dumps(packet)
        z = zlib.compress(p)
        self.client.publish(self.name, z)

    def shutdown(self):
        self.client.disconnect()
        self.client.loop_stop()


class MQTTValueSub(object):
    '''
    Use MQTT to recv values on network
    pip install paho-mqtt
    '''
    def __init__(self, name, broker="iot.eclipse.org"):
        from paho.mqtt.client import Client

        self.name = name
        self.data = None
        self.client = Client()
        self.client.on_message = self.on_message
        self.client.connect(broker)
        self.client.loop_start()
        self.client.subscribe(self.name)

    def on_message(self, client, userdata, message):
        self.data = message.payload

    def run(self):
        if self.data is None:
            return None
        p = zlib.decompress(self.data)
        obj = pickle.loads(p)

        if self.name == obj['name']:
            self.last = obj['val'] 
            return obj['val']

    def shutdown(self):
        self.client.disconnect()
        self.client.loop_stop()


def test_pub_sub(ip):
    
    if ip is None:
        print("publishing test..")
        p = ZMQValuePub('test')
        import math
        theta = 0.0
        s = time.time()

        while True:
            v = (time.time() - s, math.sin(theta), math.cos(theta), math.tan(theta))
            theta += 0.1
            p.run(v)
            time.sleep(0.1)

    else:
        print("subscribing test..", ip)
        s = ZMQValueSub('test', ip=ip)

        while True:
            res = s.run()
            print("got:", res)
            time.sleep(1)

def test_udp_broadcast(ip):
    
    if ip is None:
        print("udp broadcast test..")
        p = UDPValuePub('camera')
        import numpy as np
        print("creating test imgage to send..")
        from donkeycar.parts.camera import PiCamera
        from donkeycar.parts.image import ImgArrToJpg
        cam = PiCamera(160, 120, 3, framerate=4)
        img_conv = ImgArrToJpg()
        time.sleep(1)
        
        while True:
            cam_img = cam.run()
            jpg = img_conv.run(cam_img)
            print("sending", len(jpg), "bytes")
            p.run(jpg)
            time.sleep(0.5)

    else:
        print("udp listen test..", ip)
        s = UDPValueSub('camera')

        while True:
            res = s.run()
            time.sleep(0.1)

if __name__ == "__main__":
    import time
    import sys

    #usage:
    #  for subscriber test, pass ip arg like:
    # python network.py ip=localhost
    #
    #  for publisher test, pass no args
    # python network.py

    ip = None

    for arg in sys.argv:
        if "ip=" in arg:
            ip = arg[3:]

    #test_pub_sub(ip)
    test_udp_broadcast(ip)
