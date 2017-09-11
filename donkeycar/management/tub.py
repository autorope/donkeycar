'''
tub.py

Manage tubs
'''

import os
import json
import tornado


class TubManager:

    def run(self, args):
        WebServer(args[0]).start()


class WebServer(tornado.web.Application):

    def __init__(self, data_path):
        this_dir = os.path.dirname(os.path.realpath(__file__))
        static_file_path = os.path.join(this_dir, 'tub_web', 'static')
        
        handlers = [
            (r"/", tornado.web.RedirectHandler, dict(url="/tubs")),
            (r"/tubs", TubsView),
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

    def get(self):
        data = {}
        self.render("tub_web/tubs.html", **data)


class TubView(tornado.web.RequestHandler):

    def get(self, tub_id):
        data = {}
        self.render("tub_web/tub.html", **data)


class TubApi(tornado.web.RequestHandler):

    def initialize(self, data_path):
        self.data_path = data_path

    def get(self, tub_id):
        tub_path = os.path.join(self.data_path, tub_id)

        tub_json = os.path.join(tub_path, 'tub.json')
        if not os.path.isfile(tub_json):
            seqs = [ int(f.split("_")[0]) for f in os.listdir(tub_path) if f.endswith('.jpg') ]
            seqs.sort()
            with open(tub_json, 'w') as outfile:
                json.dump({'slices': [seqs]}, outfile)

        with open(tub_json,'r') as f:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.write(f.read())
