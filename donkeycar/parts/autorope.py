
import time
import requests
from six.moves.urllib import parse
import calendar
import datetime

from ..log import get_logger

logger = get_logger(__name__)


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


class AutoropeSession:

    def __init__(self,
                 token,
                 car_id,
                 controller_url=None,
                 api_base='https://rope.donkeycar.com/api/'):

        self.auth_token = token
        self.car_id = car_id
        self.connected = False
        self.api_base = api_base

        try:
            self.session_id = self.start_new_session(controller_url=controller_url)
            logger.info('started new autorope session {}'.format(self.session_id))
        except Exception as e:
            logger.info('Autorope part was unable to load. Goto rope.donkeycar.com for instructions')
            logger.info(e)

    def start_new_session(self, controller_url=None):
        resp = self.post_request('sessions/',
                                 {
                                     'bot_name': self.car_id,
                                     'controller_url': controller_url
                                 }
                                 )
        if resp.status_code == 200:
            resp_js = resp.json()
            self.session_id = resp_js.get('id')
            return self.session_id
        else:
            logger.info(resp.text)
            return None

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
        # combine default params and given params
        params_all = {}
        params_all.update(params)

        abs_url = self.api_base + url
        encoded_params = parse.urlencode(list(_api_encode(params_all)))
        abs_url = _build_api_url(abs_url, encoded_params)

        # logger.info('abs_url: {}'.format(abs_url))
        headers = self._build_headers(supplied_headers)

        logger.info(headers)
        logger.info(abs_url)
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
        logger.info(abs_url)
        resp = requests.post(abs_url, json=data, headers=headers, files=files)
        return resp
