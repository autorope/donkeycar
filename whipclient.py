
import requests
from datetime import datetime as dt
import dateutil.parser
import time


BASE_URL = 'http://localhost:8000/'

class Whip():
       
    cookies = {}
    headers = {}
    
    def __init__(self, base_url=BASE_URL):
        self.login_url = base_url + 'accounts/login/'
        self.record_url = base_url + 'api/record/'
        self.autodrive_url = base_url + 'api/drive/'
    
    def login(self, username, password):
        '''
        Gets the cookies and headers necessary to submit post requests
        to the django server. 
        '''        

        # Retrieve the CSRF token first, cookies=cookies
        client = requests.session()
        client.get(self.login_url)  # sets cookie

        if 'csrftoken' in client.cookies: 
            csrftoken = client.cookies['csrftoken']
        else:
            raise AssertionError('Could not load csrftoken. Make sure your credentials are correct.')

        self.cookies = dict(client.cookies)
        self.headers = { "X-CSRFToken":csrftoken}
        
        
        
    def record(self, img, env, angle, speed):
        '''Accepts: image and control attributes and saves them to learn how to drive.'''

        #load features
        data = {
                'time':dt.utcnow().isoformat(),
                'env': env,
                'angle': angle,
                'speed': speed
                }

        r = requests.post(self.record_url, files={'img': img}, data=data, 
                          headers=self.headers, cookies=self.cookies)
        
        return r
        
        
    def autodrive(self, img, env='sidewalk'):

        data = {
        'time':dt.utcnow().isoformat(),
        'env': env,
        }
        
        print(data['time'])

        r = requests.post(self.autodrive_url, files={'img': img}, data=data, 
                          headers=self.headers, cookies=self.cookies)
        
        return r
