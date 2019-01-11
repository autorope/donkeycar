import socket
import zlib, pickle
import zmq

class ValuePub(object):
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

class ValueSub(object):
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


class UDPBroadcast(object):
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
        z = z[:128]
        self.server.sendto(z, ('<broadcast>', self.port))

    def shutdown(self):
        self.server.close()

class UDPListenBroadcast(object):
    '''
    Use Zero Message Queue (zmq) to subscribe to value messages from a remote publisher
    '''
    def __init__(self, name, port = 37021, return_last=True):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.bind(("", port))
        self.name = name
        self.return_last = return_last
        self.last = None

    def run(self):
        data, addr = self.client.recvfrom(1024 * 65)
        print("got", len(data), "bytes")
        if len(data) > 0:
            p = zlib.decompress(data)
            obj = pickle.loads(p)

            if self.name == obj['name']:
                self.last = obj['val'] 
                return obj['val']

        if self.return_last:
            return self.last
        return None

    def shutdown(self):
        self.client.close()


def test_pub_sub(ip):
    
    if ip is None:
        print("publishing test..")
        p = ValuePub('test')
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
        s = ValueSub('test', ip=ip)

        while True:
            res = s.run()
            print("got:", res)
            time.sleep(1)

def test_udp_broadcast(ip):
    
    if ip is None:
        print("udp broadcast test..")
        p = UDPBroadcast('test')
        import math
        theta = 0.0
        s = time.time()

        while True:
            v = (time.time() - s, math.sin(theta), math.cos(theta), math.tan(theta))
            theta += 0.1
            p.run(v)
            time.sleep(0.1)

    else:
        print("udp listen test..", ip)
        s = UDPListenBroadcast('test')

        while True:
            res = s.run()
            print("got:", res)
            time.sleep(1)

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
