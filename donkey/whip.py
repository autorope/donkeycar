import time
import json
import io

import requests
import tornado.ioloop
import tornado.web

from PIL import Image


from utils import image as image_utils


class WhipClient():
    '''
    Class used by vehicle to send driving data and recieve predictions.
    '''
       
    
    def __init__(self, remote_url, session, model):

        self.record_url = remote_url + '/drive/'

        
        
    def post(self, img, angle, speed, milliseconds):
        '''
        Accepts: image and control attributes and saves 
        them to learn how to drive.'''

        #load features
        data = {
                'angle': angle,
                'speed': speed,
                'milliseconds': milliseconds
                }

        r = requests.post(self.record_url, 
                            files={'img': image_utils.img_to_binary(img), 
                                    'json': json.dumps(data)}) #hack to put json in file
        
        data = json.loads(r.text)
        angle = int(float(data['angle']))
        speed = int(float(data['speed']))
        print('drive client: %s' %r.text)

        return angle, speed





class WhipServer():
    '''
    Class used to create server that accepts driving data, records it, 
    runs a predictor and returns the predictions.
    '''
    
    def __init__(self, recorder, predictor):

        self.port = 8886
        self.recorder = recorder
        self.predictor = predictor

        pass
        
        
    def start(self):
        '''
        Start the webserver.
        '''

        #load features
        app = tornado.web.Application([
            (r"/", IndexHandler),
            #Here we pass in self so the webserve can update angle and speed asynch
            (r"/drive/?(?P<session>[A-Za-z0-9-]+)?/?(?P<model>[A-Za-z0-9-]+)?", 
                    DriveHandler, 
                    dict(predictor=self.predictor, recorder=self.recorder))       
            ])

        app.listen(self.port)
        tornado.ioloop.IOLoop.instance().start()

        return True



class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")



class DriveHandler(tornado.web.RequestHandler):
    def initialize(self, recorder, predictor):
        #the parrent controller
         self.predictor = predictor
         self.recorder = recorder

    def post(self, session, model):
        '''
        Receive post requests as user changes the angle
        and speed of the vehicle on a the controller webpage
        '''
        img = self.request.files['img'][0]['body']
        img = Image.open(io.BytesIO(img))

        #Hack to take json from a file
        data = json.loads(self.request.files['json'][0]['body'].decode("utf-8") )

        c_angle = data['angle']
        c_speed = data['speed']
        milliseconds = data['milliseconds']
        print('angle: %s,  speed: %s ' %(c_angle, c_speed))

        self.recorder.record(img, 
                            c_angle,
                            c_speed, 
                            milliseconds)

        arr = image_utils.img_to_greyarr(img)
        p_angle, p_speed = self.predictor.predict(arr)


        self.write(json.dumps({'angle': str(p_angle), 'speed': str(p_angle)}))
