
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
        self.values = None

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
        return obj


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

        while True:
            p.run("hi there")
            time.sleep(1)

    else:
        print("subscribing test..", ip)
        s = ValueSub('test', ip=ip)

        while True:
            res = s.run()
            print("got:", res)
            time.sleep(1)
