'''
tub.py

Manage tubs
'''

import json
import os
import sys
import time
from pathlib import Path
from stat import S_ISREG, ST_ATIME, ST_CTIME, ST_MODE, ST_MTIME

import tornado.web

from donkeycar.parts.tub_v2 import Tub


class TubManager:

    def run(self, args):
        WebServer(args[0]).start()


class WebServer(tornado.web.Application):

    def __init__(self, data_path):
        if not os.path.exists(data_path):
            raise ValueError('The path {} does not exist.'.format(data_path))

        this_dir = os.path.dirname(os.path.realpath(__file__))
        static_file_path = os.path.join(this_dir, 'tub_web', 'static')

        handlers = [
            (r"/", tornado.web.RedirectHandler, dict(url="/tubs")),
            (r"/tubs", TubsView, dict(data_path=data_path)),
            (r"/tubs/?(?P<tub_id>[^/]+)?", TubView),
            (r"/api/tubs/?(?P<tub_id>[^/]+)?", TubApi, dict(data_path=data_path)),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": static_file_path}),
            (r"/tub_data/(.*)", tornado.web.StaticFileHandler, {"path": data_path}),
            ]

        settings = {'debug': True}

        super().__init__(handlers, **settings)

    def start(self, port=8886):
        self.port = int(port)
        self.listen(self.port)
        print('Listening on {}...'.format(port))
        tornado.ioloop.IOLoop.instance().start()


class TubsView(tornado.web.RequestHandler):

    def initialize(self, data_path):
        self.data_path = data_path

    def get(self):
        import fnmatch
        dir_list = fnmatch.filter(os.listdir(self.data_path), '*')
        dir_list.sort()
        data = {"tubs": dir_list}
        self.render("tub_web/tubs.html", **data)


class TubView(tornado.web.RequestHandler):

    def get(self, tub_id):
        data = {}
        self.render("tub_web/tub.html", **data)


class TubApi(tornado.web.RequestHandler):

    def initialize(self, data_path):
        path = Path(os.path.expanduser(data_path))
        self.data_path = path.absolute()

    def clips_of_tub(self, tub_path):
        tub = Tub(tub_path)

        clips = []
        for record in tub:
            index = record['_index']
            images_relative_path = os.path.join(Tub.images(), record['cam/image_array'])
            record['cam/image_array'] = images_relative_path
            clips.append(record)

        return [clips]

    def get(self, tub_id):
        base_path = os.path.join(self.data_path, tub_id)
        clips = self.clips_of_tub(base_path)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps({'clips': clips}))

    def post(self, tub_id):
        tub_path = os.path.join(self.data_path, tub_id)
        tub = Tub(tub_path)
        old_clips = self.clips_of_tub(tub_path)
        new_clips = tornado.escape.json_decode(self.request.body)

        import itertools
        old_frames = list(itertools.chain(*old_clips))
        old_indexes = set()
        for frame in old_frames:
            old_indexes.add(frame['_index'])

        new_frames = list(itertools.chain(*new_clips['clips']))
        new_indexes = set()
        for frame in new_frames:
            new_indexes.add(frame['_index'])

        frames_to_delete = [index for index in old_indexes if index not in new_indexes]
        tub.delete_records(frames_to_delete)
