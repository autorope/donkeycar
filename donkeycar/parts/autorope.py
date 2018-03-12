
import time
import requests
from six.moves.urllib import parse
import calendar
import datetime
import json
import socket
def _api_encode(data):
    for key, value in data.items():
        if value is None:
            continue
        elif isinstance(value, datetime.datetime):
            yield (key, _encode_datetime(value))
        else:
            yield (key, value)


def _build_api_url(url, query):
    scheme, netloc, path, base_query, fragment = parse.urlsplit(url)
    if base_query:
        query = str('%s&%s' % (base_query, query))

    return parse.urlunsplit((scheme, netloc, path, query, fragment))


def _encode_datetime(dttime):
    if dttime.tzinfo and dttime.tzinfo.utcoffset(dttime) is not None:
        utc_timestamp = calendar.timegm(dttime.utctimetuple())
    else:
        utc_timestamp = time.mktime(dttime.timetuple())

    return int(utc_timestamp)


class Autorope_Connection():

    api_base = 'http://rope.donkeycar.com/api/'

    def __init__(self, token, car_id):
        self.auth_token=token
        self.car_id = car_id
        self.connected = False

        car_ip = ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0])

        resp = self.post_request('sessions/',
                                          {'bot': self.car_id, 'controller_url': 'http://{}:8887'.format(car_ip)})

        resp_js = resp.json()
        self.session_id = resp_js.get('id')



    def update(self):
        self.measurements = self.lidar.iter_measurments(500)
        for new_scan, quality, angle, distance in self.measurements:
            angle = int(angle)
            self.frame[angle] = 2 * distance / 3 + self.frame[angle] / 3
            if not self.on:
                break

    def run_threaded(self):
        return self.frame


    def _build_headers(self, headers={}):

        auth_header = {'Authorization': 'Token {}'.format(self.auth_token)}
        headers.update(auth_header)
        return headers


    def get_request(self, url, params={}, supplied_headers={}, format='json'):

        #combine default params and given params
        params_all = {}
        params_all.update(params)

        abs_url = self.api_base + url
        encoded_params = parse.urlencode(list(_api_encode(params_all)))
        abs_url = _build_api_url(abs_url, encoded_params)

        #print('abs_url: {}'.format(abs_url))
        headers = self._build_headers(supplied_headers)

        print(headers)
        print(abs_url)
        resp = requests.get(abs_url, headers=headers)
        if format == 'json':
            return resp
        elif format == 'text':
            return resp.text
        elif format == 'gdf':
            import tempfile
            import geopandas as gp
            file = tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w')
            file.write(resp.text)
            file.close()

            gdf = gp.read_file(file.name)
            return gdf


    def post_request(self, url, data, params=None, supplied_headers={}, files=None):
        abs_url = self.api_base + url

        encoded_params = parse.urlencode(list(_api_encode(params or {})))
        abs_url = _build_api_url(abs_url, encoded_params)
        headers = self._build_headers(supplied_headers)
        print(abs_url)
        resp = requests.post(abs_url, json=data, headers=headers, files=files)
        return resp
