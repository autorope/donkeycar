import socket
import zlib, pickle
import zmq
import time

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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)    
        self.sock.settimeout(0.2)
        self.sock.bind(("", 44444))

    def run(self, values):
        packet = { "name": self.name, "val" : values }
        p = pickle.dumps(packet)
        z = zlib.compress(p)
        #print("broadcast", len(z), "bytes to port", self.port)
        self.sock.sendto(z, ('<broadcast>', self.port))

    def shutdown(self):
        self.sock.close()

class UDPValueSub(object):
    '''
    Use UDP to listen for broadcase packets
    '''
    def __init__(self, name, port = 37021, def_value=None):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.bind(("", port))
        print("listening for UDP broadcasts on port", port)
        self.name = name
        self.last = def_value
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
        #print("got", len(data), "bytes")
        if len(data) > 0:
            p = zlib.decompress(data)
            obj = pickle.loads(p)

            if self.name == obj['name']:
                self.last = obj['val']


    def shutdown(self):
        self.running = False
        self.client.close()

import select

class TCPServeValue(object):
    '''
    Use tcp to serve values on local network
    '''
    def __init__(self, name, port = 3233):
        self.name = name
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.setblocking(False)
        self.sock.bind(("0.0.0.0", port))
        self.sock.listen(3)
        print("serving value:", name, "on port:", port)
        self.clients = []

    def send(self, sock, msg):
        try:
            sock.sendall(msg)
        except ConnectionResetError:
            print("client dropped connection")
            self.clients.remove(sock)

        #print("sent", len(msg), "bytes")

    def run(self, values):
        timeout = 0.05
        ready_to_read, ready_to_write, in_error = \
               select.select(
                  [self.sock],
                  self.clients,
                  [],
                  timeout)
            
        if len(ready_to_write) > 0:
            packet = { "name": self.name, "val" : values }
            p = pickle.dumps(packet)
            z = zlib.compress(p)
            for client in ready_to_write:
                try:
                    self.send(client, z)
                except BrokenPipeError or ConnectionResetError:
                    print("client dropped connection")
                    self.clients.remove(client)
        
        if self.sock in ready_to_read:
            client, addr = self.sock.accept()
            print("got connection from", addr)
            self.clients.append(client)

        if len(in_error) > 0:
            print("clients gone")
            for sock in in_error:
                self.clients.remove(sock)

    def shutdown(self):
        self.sock.close()


class TCPClientValue(object):
    '''
    Use tcp to get values on local network
    '''
    def __init__(self, name, host, port=3233):
        self.name = name
        self.port = port
        self.addr = (host, port)
        self.sock = None
        self.connect()
        self.timeout = 0.05
        self.lastread = time.time()

    def connect(self):
        print("attempting connect to", self.addr)
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(self.addr)
        except ConnectionRefusedError:
            print('server down')
            time.sleep(3.0)
            self.sock = None
            return False
        print("connected!")
        self.sock.setblocking(False)
        return True

    def is_connected(self):
        return self.sock is not None

    def read(self, sock):
        data = self.sock.recv(64 * 1024)

        ready_to_read, ready_to_write, in_error = \
        select.select(
            [self.sock],
            [],
            [],
            self.timeout)

        while len(ready_to_read) == 1:
            more_data = self.sock.recv(64 * 1024)
            if len(more_data) == 0:
                break
            data = data + more_data

            ready_to_read, ready_to_write, in_error = \
            select.select(
                [self.sock],
                [],
                [],
                self.timeout)

        return data

    def reset(self):
        self.sock.close()
        self.sock = None
        self.lastread = time.time()
            
 
    def run(self):

        time_since_last_read = abs(time.time() - self.lastread)
        
        if self.sock is None:
            if not self.connect():
                return None
        elif time_since_last_read > 5.0: 
            print("error: no data from server. may have died")
            self.reset()
            return None

        ready_to_read, ready_to_write, in_error = \
               select.select(
                  [self.sock],
                  [self.sock],
                  [],
                  self.timeout)

        if len(in_error) > 0:
            print("error: server may have died")
            self.reset()
            return None

        if len(ready_to_read) == 1:
            try:
                data = self.read(self.sock)
                #print("got", len(data), "bytes")
                self.lastread = time.time()
                p = zlib.decompress(data)
                obj = pickle.loads(p)
            except Exception as e:
                print(e)
                print("error: server may have died")
                self.reset()
                return None

            if self.name == obj['name']:
                self.last = obj['val'] 
                return obj['val']

        if len(in_error) > 0:
            print("connection closed")
            self.reset()

        return None

    def shutdown(self):
        self.sock.close()

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
        print("connecting to broker", broker)
        self.client.connect(broker)
        self.client.loop_start()
        print("connected.")

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
    def __init__(self, name, broker="iot.eclipse.org", def_value=None):
        from paho.mqtt.client import Client

        self.name = name
        self.data = None
        self.client = Client(clean_session=True)
        self.client.on_message = self.on_message
        print("(clean_session) connecting to broker", broker)
        self.client.connect(broker)
        self.client.loop_start()
        self.client.subscribe(self.name)
        self.def_value = def_value
        print("connected.")

    def on_message(self, client, userdata, message):
        self.data = message.payload
        
    def run(self):
        if self.data is None:
            return self.def_value

        p = zlib.decompress(self.data)
        obj = pickle.loads(p)

        if self.name == obj['name']:
            self.last = obj['val']
            #print("steering, throttle", obj['val'])
            return obj['val']
            
        return self.def_value

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

def test_tcp_client_server(ip):

    if ip is None:
        p = TCPServeValue("camera")
        from donkeycar.parts.camera import PiCamera
        from donkeycar.parts.image import ImgArrToJpg
        cam = PiCamera(160, 120, 3, framerate=4)
        img_conv = ImgArrToJpg()
        while True:
            cam_img = cam.run()
            jpg = img_conv.run(cam_img)
            p.run(jpg)
            time.sleep(0.1)
    else:
        c = TCPClientValue("camera", ip)
        while True:
            c.run()
            time.sleep(0.01)

def test_mqtt_pub_sub(ip):
    
    if ip is None:
        print("publishing test..")
        p = MQTTValuePub('donkey/camera')
        from donkeycar.parts.camera import PiCamera
        from donkeycar.parts.image import ImgArrToJpg
        cam = PiCamera(160, 120, 3, framerate=4)
        img_conv = ImgArrToJpg()
        while True:
            cam_img = cam.run()
            jpg = img_conv.run(cam_img)
            p.run(jpg)
            time.sleep(0.1)

    else:
        print("subscribing test..")
        s = MQTTValueSub('donkey/camera')

        while True:
            res = s.run()
            print("got:", res)
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
    #test_udp_broadcast(ip)
    #test_mqtt_pub_sub(ip)
    test_tcp_client_server(ip)
    

