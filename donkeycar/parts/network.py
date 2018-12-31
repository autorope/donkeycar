
import zlib, pickle
import zmq

class ValuePub(object):
    '''
    Use Zero Message Queue (zmq) to publish values
    '''
    def __init__(self, name, port = 5556):
        context = zmq.Context()
        self.name = name
        self.socket = context.socket(zmq.PUB)
        self.socket.bind("tcp://*:%d" % port)
    
    def run(self, values):
        packet = { "name": self.name, "val" : values }
        p = pickle.dumps(packet)
        z = zlib.compress(p)
        self.socket.send(z)

    def shutdown(self):
        self.socket.close()
        context = zmq.Context()
        context.destroy()

class ValueSub(object):
    '''
    Use Zero Message Queue (zmq) to subscribe to value messages from a remote publisher
    '''
    def __init__(self, name, ip, port = 5556):
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://%s:%d" % (ip, port))
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.name = name

    def run(self):
        '''
        poll socket for input. returns None when nothing was recieved
        otherwize returns packet data
        '''
        try:
            z = self.socket.recv(flags=zmq.NOBLOCK)
        except zmq.Again as e:
            return None

        p = zlib.decompress(z)        
        obj = pickle.loads(p)

        if self.name == obj['name']:
            return obj['val']

        return None

    def shutdown(self):
        self.socket.close()
        context = zmq.Context()
        context.destroy()


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
