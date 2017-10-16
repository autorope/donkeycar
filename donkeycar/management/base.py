#!/usr/bin/env python3
"""
Upload a file to S3 (requires amazon credentials).

Usage:
     donkey <command> [--file_path=<file_path>]

Options:
  --file_path=<file_path> name of dataset file to save.
  --bucket=<bucket>  name of S3 bucket to upload data. [default: donkey_resources].
"""

from docopt import docopt
import sys
import os
import socket
import shutil
import argparse

from .tub import TubManager

PACKAGE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_PATH = os.path.join(PACKAGE_PATH, 'templates')

def make_dir(path):
    real_path = os.path.expanduser(path)
    print('making dir ', real_path)
    if not os.path.exists(real_path):
        os.makedirs(real_path)
    return real_path


def load_config(config_path):
    import donkeycar as dk

    '''
    load a config from the given path
    '''
    conf = os.path.expanduser(config_path)

    if not os.path.exists(conf):
        print("No config file at location: %s. Add --config to specify\
                location or run from dir containing config.py." % conf)
        return None

    try:
        cfg = dk.load_config(conf)
    except:
        print("Exception while loading config from", conf)
        return None

    return cfg


class BaseCommand():
    pass


class CreateCar(BaseCommand):
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='createcar', usage='%(prog)s [options]')
        parser.add_argument('--path', help='path where to create car folder')
        parser.add_argument('--template', help='name of car template to use')
        parser.add_argument('--overwrite', action='store_true', help='should replace existing files')
        
        parsed_args = parser.parse_args(args)
        return parsed_args
        
    def run(self, args):
        args = self.parse_args(args)
        self.create_car(path=args.path, template=args.template, overwrite=args.overwrite)
    
    def create_car(self, path, template, overwrite=False):
        """
        This script sets up the folder struction for donkey to work. 
        It must run without donkey installed so that people installing with
        docker can build the folder structure for docker to mount to.
        """
        
        path = path or '~/mydonkey'
        template = template or 'donkey2'
        
        print("Creating car folder: {}".format(path))
        path = make_dir(path)
        
        print("Creating data & model folders.")
        folders = ['models', 'data', 'logs']
        folder_paths = [os.path.join(path, f) for f in folders]   
        for fp in folder_paths:
            make_dir(fp)
            
        #add car application and config files if they don't exist
        app_template_path = os.path.join(TEMPLATES_PATH, template+'.py')
        config_template_path = os.path.join(TEMPLATES_PATH, 'config_defaults.py')
        car_app_path = os.path.join(path, 'manage.py')
        car_config_path = os.path.join(path, 'config.py')
        
        if os.path.exists(car_app_path) and not overwrite:
            print('Car app already exists. Delete it and rerun createcar to replace.')
        else:
            print("Copying car application template: {}".format(template))
            shutil.copyfile(app_template_path, car_app_path)
            
        if os.path.exists(car_config_path) and not overwrite:
            print('Car config already exists. Delete it and rerun createcar to replace.')
        else:
            print("Copying car config defaults. Adjust these before starting your car.")
            shutil.copyfile(config_template_path, car_config_path)
 
        print("Donkey setup complete.")


class UploadData(BaseCommand):
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='uploaddata', usage='%(prog)s [options]')
        parser.add_argument('--url', help='path where to create car folder')
        parser.add_argument('--template', help='name of car template to use')
        
        parsed_args = parser.parse_args(args)
        return parsed_args



class FindCar(BaseCommand):
    def parse_args(self, args):
        pass        

        
    def run(self, args):
        print('Looking up your computer IP address...')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80))
        ip = s.getsockname()[0] 
        print('Your IP address: %s ' %s.getsockname()[0])
        s.close()
        
        print("Finding your car's IP address...")
        cmd = "sudo nmap -sP " + ip + "/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'"
        print("Your car's ip address is:" )
        os.system(cmd)
        
        
        
class CalibrateCar(BaseCommand):    
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='calibrate', usage='%(prog)s [options]')
        parser.add_argument('--channel', help='The channel youd like to calibrate [0-15]')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        import donkeycar as dk
    
        args = self.parse_args(args)
        channel = int(args.channel)
        c = dk.parts.PCA9685(channel)
        
        for i in range(10):
            pmw = int(input('Enter a PWM setting to test(0-1500)'))
            c.run(pmw)



class MakeMovie(BaseCommand):    
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='makemovie')
        parser.add_argument('--tub', help='The tub to make movie from')
        parser.add_argument('--out', default='tub_movie.mp4', help='The movie filename to create. default: tub_movie.mp4')
        parser.add_argument('--config', default='./config.py', help='location of config file to use. default: ./config.py')
        parsed_args = parser.parse_args(args)
        return parsed_args, parser

    def run(self, args):
        '''
        Load the images from a tub and create a movie from them.
        Movie
        '''
        import donkeycar as dk
        import moviepy.editor as mpy
        import os

        args, parser = self.parse_args(args)

        if args.tub is None:
            parser.print_help()
            return            

        cfg = load_config(args.config)

        if cfg is None:
            return

        self.tub = dk.parts.Tub(args.tub)
        self.num_rec = self.tub.get_num_records()
        self.iRec = 0

        print('making movie', args.out, 'from', self.num_rec, 'images')
        clip = mpy.VideoClip(self.make_frame, duration=(self.num_rec//cfg.DRIVE_LOOP_HZ) - 1)
        clip.write_videofile(args.out,fps=cfg.DRIVE_LOOP_HZ)

        print('done')

    def make_frame(self, t):
        '''
        Callback to return an image from from our tub records.
        This is called from the VideoClip as it references a time.
        We don't use t to reference the frame, but instead increment
        a frame counter. This assumes sequential access.
        '''
        self.iRec = self.iRec + 1
        
        if self.iRec >= self.num_rec - 1:
            return None

        rec = self.tub.get_record(self.iRec)
        image = rec['cam/image_array']
        
        return image # returns a 8-bit RGB array



class Sim(BaseCommand):
    '''
    Start a websocket SocketIO server to talk to a donkey simulator    
    '''
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='sim')
        parser.add_argument('--model', help='the model to use for predictions')
        parser.add_argument('--config', default='./config.py', help='location of config file to use. default: ./config.py')
        parser.add_argument('--type', default='categorical', help='model type to use when loading. categorical|linear')
        parser.add_argument('--top_speed', default='3', help='what is top speed to drive')
        parsed_args = parser.parse_args(args)
        return parsed_args, parser

    def run(self, args):
        '''
        Start a websocket SocketIO server to talk to a donkey simulator
        '''
        import socketio
        import donkeycar as dk

        args, parser = self.parse_args(args)

        cfg = load_config(args.config)

        if cfg is None:
            return

        if args.type == "categorical":
            kl = dk.parts.KerasCategorical()
        elif args.type == "linear":
            kl = dk.parts.KerasLinear(num_outputs=2)
        else:
            print("didn't recognice type:", args.type)
            return

        #can provide an optional image filter part
        img_stack = None

        #load keras model
        kl.load(args.model)  

        #start socket server framework
        sio = socketio.Server()

        top_speed = float(args.top_speed)

        #start sim server handler
        ss = dk.parts.sim_server.SteeringServer(sio, kpart=kl, top_speed=top_speed, image_part=img_stack)
                
        #register events and pass to server handlers

        @sio.on('telemetry')
        def telemetry(sid, data):
            ss.telemetry(sid, data)

        @sio.on('connect')
        def connect(sid, environ):
            ss.connect(sid, environ)

        ss.go(('0.0.0.0', 9090))




def execute_from_command_line():
    
    commands = {
            'createcar': CreateCar,
            'findcar': FindCar,
            'calibrate': CalibrateCar,
            'tub': TubManager,
            'makemovie': MakeMovie,
            'sim': Sim,
            #'calibratesteering': CalibrateSteering,
                }
    
    args = sys.argv[:]
    command_text = args[1]
    
    if command_text in commands.keys():
        command = commands[command_text]
        c = command()
        c.run(args[2:])
    else:
        print('The availible commands are:')
        print(list(commands.keys()))
        
    
    
