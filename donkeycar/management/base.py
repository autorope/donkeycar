
import sys
import os
import socket
import shutil
import argparse
import json
import time

import donkeycar as dk
from donkeycar.parts.datastore import Tub
from donkeycar.utils import *
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


class BaseCommand(object):
    pass


class CreateCar(BaseCommand):
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='createcar', usage='%(prog)s [options]')
        parser.add_argument('--path', default=None, help='path where to create car folder')
        parser.add_argument('--template', default=None, help='name of car template to use')
        parser.add_argument('--overwrite', action='store_true', help='should replace existing files')
        
        parsed_args = parser.parse_args(args)
        return parsed_args
        
    def run(self, args):
        args = self.parse_args(args)
        self.create_car(path=args.path, template=args.template, overwrite=args.overwrite)
    
    def create_car(self, path, template='donkey2', overwrite=False):
        """
        This script sets up the folder struction for donkey to work. 
        It must run without donkey installed so that people installing with
        docker can build the folder structure for docker to mount to.
        """

        #these are neeeded incase None is passed as path
        path = path or '~/d2'
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
        train_template_path = os.path.join(TEMPLATES_PATH, 'train.py')
        car_app_path = os.path.join(path, 'manage.py')
        car_config_path = os.path.join(path, 'config.py')
        train_app_path = os.path.join(path, 'train.py')
        
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
 
        if os.path.exists(train_app_path) and not overwrite:
            print('Train already exists. Delete it and rerun createcar to replace.')
        else:
            print("Copying train script. Adjust these before starting your car.")
            shutil.copyfile(train_template_path, train_app_path)
 
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
        from donkeycar.parts.actuator import PCA9685
    
        args = self.parse_args(args)
        channel = int(args.channel)
        c = PCA9685(channel)
        
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
        import moviepy.editor as mpy


        args, parser = self.parse_args(args)

        if args.tub is None:
            parser.print_help()
            return            

        conf = os.path.expanduser(args.config)

        if not os.path.exists(conf):
            print("No config file at location: %s. Add --config to specify\
                 location or run from dir containing config.py." % conf)
            return

        try:
            cfg = dk.load_config(conf)
        except:
            print("Exception while loading config from", conf)
            return

        self.tub = Tub(args.tub)
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
        from donkeycar.parts.simulation import SteeringServer
        from donkeycar.parts.keras import KerasCategorical, KerasLinear,\
            Keras3D_CNN, KerasRNN_LSTM

        args, parser = self.parse_args(args)

        cfg = load_config(args.config)

        if cfg is None:
            return

        #TODO: this logic should be in a pilot or model handler part.
        if args.type == "categorical":
            kl = KerasCategorical()
        elif args.type == "linear":
            kl = KerasLinear(num_outputs=2)
        elif args.type == "rnn":
            kl = KerasRNN_LSTM(image_w=cfg.IMAGE_W,
                image_h=cfg.IMAGE_H,
                image_d=cfg.IMAGE_DEPTH,
                seq_length=cfg.SEQUENCE_LENGTH, num_outputs=2)
        elif args.type == "3d":
            kl = Keras3D_CNN(image_w=cfg.IMAGE_W,
                image_h=cfg.IMAGE_H,
                image_d=cfg.IMAGE_DEPTH,
                seq_length=cfg.SEQUENCE_LENGTH,
                num_outputs=2)
        else:
            print("didn't recognize type:", args.type)
            return

        #can provide an optional image filter part
        img_stack = None

        #load keras model
        kl.load(args.model)  

        #start socket server framework
        sio = socketio.Server()

        top_speed = float(args.top_speed)

        #start sim server handler
        ss = SteeringServer(sio, kpart=kl, top_speed=top_speed, image_part=img_stack)
                
        #register events and pass to server handlers

        @sio.on('telemetry')
        def telemetry(sid, data):
            ss.telemetry(sid, data)

        @sio.on('connect')
        def connect(sid, environ):
            ss.connect(sid, environ)

        ss.go(('0.0.0.0', 9090))



class TubCheck(BaseCommand):
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='tubcheck', usage='%(prog)s [options]')
        parser.add_argument('tubs', nargs='+', help='paths to tubs')
        parser.add_argument('--fix', action='store_true', help='remove problem records')
        parser.add_argument('--delete_empty', action='store_true', help='delete tub dir with no records')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def check(self, tub_paths, fix=False, delete_empty=False):
        '''
        Check for any problems. Looks at tubs and find problems in any records or images that won't open.
        If fix is True, then delete images and records that cause problems.
        '''
        tubs = [Tub(path) for path in tub_paths]

        for tub in tubs:
            tub.check(fix=fix)
            if delete_empty and tub.get_num_records() == 0:
                import shutil
                print("removing empty tub", tub.path)
                shutil.rmtree(tub.path)

    def run(self, args):
        args = self.parse_args(args)
        self.check(args.tubs, args.fix, args.delete_empty)


class ShowHistogram(BaseCommand):

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='tubhist', usage='%(prog)s [options]')
        parser.add_argument('--tub', nargs='+', help='paths to tubs')
        parser.add_argument('--record', default=None, help='name of record to create histogram')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def show_histogram(self, tub_paths, record_name):
        '''
        Produce a histogram of record type frequency in the given tub
        '''
        from matplotlib import pyplot as plt
        from donkeycar.parts.datastore import TubGroup

        tg = TubGroup(tub_paths=tub_paths)
        if record_name is not None:
            tg.df[record_name].hist(bins=50)
        else:
            tg.df.hist(bins=50)

        plt.savefig(os.path.basename(model_path) + '_hist_%s.png' % record_name)
        plt.show()

    def run(self, args):
        args = self.parse_args(args)
        args.tub = ','.join(args.tub)
        self.show_histogram(args.tub, args.record)


class ConSync(BaseCommand):
    '''
    continuously rsync data
    '''
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='consync', usage='%(prog)s [options]')
        parser.add_argument('--dir', default='./cont_data/', help='paths to tubs')
        parser.add_argument('--delete', default='y', help='remove files locally that were deleted remotely y=yes n=no')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        cfg = load_config('config.py')
        dest_dir = args.dir
        del_arg = ""

        if args.delete == 'y':
            reply = input('WARNING:this rsync operation will delete data in the target dir: %s. ok to proceeed? [y/N]: ' % dest_dir)

            if reply != 'y' and reply != "Y":
                return
            del_arg = "--delete"

        if not dest_dir[-1] == '/' and not dest_dir[-1] == '\\':
            print("Desination dir should end with a /")
            return

        try:
            os.mkdir(dest_dir)
        except:
            pass

        while True:
            command = "rsync -aW --progress %s@%s:%s/data/ %s %s" %\
                (cfg.PI_USERNAME, cfg.PI_HOSTNAME, cfg.PI_DONKEY_ROOT, dest_dir, del_arg)

            os.system(command)
            time.sleep(5)

class ConTrain(BaseCommand):
    '''
    continuously train data
    '''
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='contrain', usage='%(prog)s [options]')
        parser.add_argument('--tub', default='./cont_data/*', help='paths to tubs')
        parser.add_argument('--model', default='./models/drive.h5', help='path to model')
        parser.add_argument('--transfer', default=None, help='path to transfer model')
        parser.add_argument('--type', default='categorical', help='type of model (linear|categorical|rnn|imu|behavior|3d)')
        parser.add_argument('--aug', action="store_true", help='perform image augmentation')        
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        cfg = load_config('config.py')
        import sys
        sys.path.append('.')
        from train import multi_train
        continuous = True
        multi_train(cfg, args.tub, args.model, args.transfer, args.type, continuous, args.aug)


class ShowPredictionPlots(BaseCommand):

    def plot_predictions(self, cfg, tub_paths, model_path, limit, model_type):
        '''
        Plot model predictions for angle and throttle against data from tubs.

        '''
        import matplotlib.pyplot as plt
        import pandas as pd

        model_path = os.path.expanduser(model_path)
        model = dk.utils.get_model_by_type(model_type, cfg)
        model.load(model_path)

        records = gather_records(cfg, tub_paths)
        user_angles = []
        user_throttles = []
        pilot_angles = []
        pilot_throttles = []       

        records = records[:limit]
        num_records = len(records)
        print('processing %d records:' % num_records)

        for record_path in records:
            with open(record_path, 'r') as fp:
                record = json.load(fp)
            img_filename = os.path.join(tub_paths, record['cam/image_array'])
            img = load_scaled_image_arr(img_filename, cfg)
            user_angle = float(record["user/angle"])
            user_throttle = float(record["user/throttle"])
            pilot_angle, pilot_throttle = model.run(img)

            user_angles.append(user_angle)
            user_throttles.append(user_throttle)
            pilot_angles.append(pilot_angle)
            pilot_throttles.append(pilot_throttle)

        angles_df = pd.DataFrame({'user_angle': user_angles, 'pilot_angle': pilot_angles})
        throttles_df = pd.DataFrame({'user_throttle': user_throttles, 'pilot_throttle': pilot_throttles})

        fig = plt.figure()

        title = "Model Predictions\nTubs: " + tub_paths + "\nModel: " + model_path
        fig.suptitle(title)

        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)

        angles_df.plot(ax=ax1)
        throttles_df.plot(ax=ax2)

        ax1.legend(loc=4)
        ax2.legend(loc=4)

        plt.savefig(model_path + '_pred.png')
        plt.show()

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='tubplot', usage='%(prog)s [options]')
        parser.add_argument('--tub', nargs='+', help='paths to tubs')
        parser.add_argument('--model', default=None, help='name of record to create histogram')
        parser.add_argument('--limit', default=1000, help='how many records to process')
        parser.add_argument('--type', default='categorical', help='how many records to process')
        parser.add_argument('--config', default='./config.py', help='location of config file to use. default: ./config.py')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        args.tub = ','.join(args.tub)
        cfg = load_config(args.config)
        self.plot_predictions(cfg, args.tub, args.model, args.limit, args.type)
        

class CreateJoystick(BaseCommand):

    def __init__(self):
        self.last_button = None
        self.last_axis = None
        self.running = False
        self.thread = None
        self.motion_axis = []
        self.ignore_axis = False
        self.ignore_buttons = False

    def poll(self):
        while self.running:
            button, button_state, axis, axis_val = self.js.poll()

            if button is not None and not self.ignore_buttons:
                print(button)
                self.last_button = button
                self.last_axis = None
            elif axis is not None and not self.ignore_axis:
                if not axis in self.motion_axis:
                    self.last_axis = axis
                    self.last_button = None

    def get_button_press(self, duration=10.0):
        self.last_button = None

        start = time.time()

        while self.last_button is None and time.time() - start < duration:
            time.sleep(0.1)

        return self.last_button

    def get_axis_move(self, duration=2.0):
        self.last_axis = None
        axis_samples = {}

        start = time.time()

        while time.time() - start < duration:
            if self.last_axis:
                if self.last_axis in axis_samples:
                    axis_samples[self.last_axis] = axis_samples[self.last_axis] + 1
                else:
                    axis_samples[self.last_axis] = 1

        most_movement = None
        most_iter = 0
        for key, value in axis_samples.items():
            if value > most_iter:
                most_movement = key
                most_iter = value

        return most_movement

    def create_joystick(self, args):
        from donkeycar.parts.controller import JoystickCreatorController

        print("Welcome to Joystick Creator Wizard. Please plug-in your controller via USB or bluetooth.")
        ret = input('Enter to continue ')
        js_cr = None

        #Get device file and create js creator helper class
        print()
        while js_cr is None:
            print("Which device file would you like to use?")
            dev_fn = input("Hit Enter for default: /dev/input/js0 or type alternate path: ")
            if len(dev_fn) is 0:
                dev_fn = '/dev/input/js0'

            print()
            print("Attempting to open device at that file...")
            try:
                js_cr = JoystickCreatorController(dev_fn=dev_fn)
                res = js_cr.init_js()
                if res:
                    print("Found and accessed input device file.")
                else:
                    js_cr = None
            except Exception as e:
                print("threw exception:" + str(e))
                js_cr = None

            if js_cr is None:
                ret = input("Failed to open device. try again? [y/N] : ")
                if len(ret) == 0 or ret == "n" or ret == "N":
                    break

        print()
        self.js = js_cr.js
        self.running = True

        import threading
        self.thread = threading.Thread(target=self.poll)
        self.thread.daemon = True
        self.thread.start()

        print("Next we are going to look for gyroscope data.")
        input("For 5 seconds, move controller and rotate on each axis. Enter to start moving: ")
        start = time.time()
        while time.time() - start < 5.0:
            if self.last_axis is not None and not self.last_axis in self.motion_axis:
                self.motion_axis.append(self.last_axis)

        print()
        if len(self.motion_axis) > 0:
            print("Ok, we found %d axes that stream gyroscope data." % len(self.motion_axis))
        else:
            print("Ok, we didn't see any events. So perhaps your controller doesn't emit gyroscope data. No problem.")
            
        print()
        print('Next we are going to name all the buttons you would like to use.')
        done = False
        self.ignore_axis = True

        while not done:
            print('Tap a button on the controller. Any previously mapped button to quit')
            
            self.get_button_press()

            if self.last_button is None:
                print("No button was pressed in last 10 seconds. It's possible that your buttons all generate axis commands.")
                ret = input("Keep mapping buttons? [Y, n]")
                if ret == 'n':
                    break
            elif 'unknown' in self.last_button:
                code_str = self.last_button.split('(')[1][:-1]
                print('got button code:', code_str)
                try:
                    code = int(code_str, 16)
                except Exception as e:
                    code = None
                    print("failed to parse code", str(e))

                if code is not None:
                    if code in self.js.button_names:
                        done = True
                        break
                    label = input("what name to give to this button: (Q to quit) ")
                    if len(label) == 0:
                        print("no name given. skipping.")
                    elif label == 'q':
                        done = True
                    else:
                        self.js.button_names[code] = label
            else:
                print('got press: ', self.last_button)

            print()

        
        print("Created button map:")
        print(self.js.button_names)

        print()
        print('Next we are going to name all the axis you would like to use.')

        done = False
        self.ignore_axis = False

        while not done:
            print('Prepare to move one axis on the controller for 2 sec.')
            ret = input("Hit Enter to begin. Q to quit. ")
            if ret == 'q':
                break
            
            most_movement = self.get_axis_move()

            if most_movement is None:
                print("Didn't detect any movement.")
                res = input("Try again? [Y/n]: ")
                if res == "n":
                    done = True
                    break
                else:
                    continue

            if 'unknown' in most_movement:
                code_str = most_movement.split('(')[1][:-1]
                print('Most movement on axis code:', code_str)
                try:
                    code = int(code_str, 16)
                except Exception as e:
                    code = None
                    print("Failed to parse code", str(e))

                if code is not None:
                    label = input("What name to give to this axis: (Q to quit) ")
                    if len(label) == 0:
                        print("No name given. skipping.")
                    elif label == 'q':
                        done = True
                    else:
                        self.js.axis_names[code] = label
            else:
                print('Got axis: ', self.last_axis)
            print()

        print("Created axis map:")
        print(self.js.axis_names)

        print()
        pyth_filename = None
        outfile = None
        while pyth_filename is None:
            print("Now we will write these values to a new python file.")
            pyth_filename = input("What is the name of python file to create joystick code? [default: joystick.py]")
            if len(pyth_filename) == 0:
                pyth_filename = 'joystick.py'
            print()
            try:
                outfile = open(pyth_filename, "wt")
            except:
                ret = input("failed to open filename. Enter another filename? [Y,n]")
                if ret == "n":
                    break
                pyth_filename = None
            print()
            
        if outfile is not None:
            classname = ("What is the name of joystick class? [default: MyJoystick] ")
            if len(classname) == 0:
                classname = "MyJoystick"
            file_header = \
            '''
            from donkeycar.parts.controller import Joystick, JoystickController


            class %s(Joystick):
                #An interface to a physical PS3 joystick available at /dev/input/js0
                def __init__(self, *args, **kwargs):
                    super(%s, self).__init__(*args, **kwargs)

            ''' % (classname, classname )

            outfile.write(file_header)

            outfile.write('        self.button_names = {\n')
            for key, value in self.js.button_names.items():
                outfile.write("            %s : '%s',\n" % (str(key), str(value)))
            outfile.write('        }\n\n\n')
            
            outfile.write('        self.axis_names = {\n')

            for key, value in self.js.axis_names.items():
                outfile.write("            %s : '%s',\n" % (str(key), str(value)))
            outfile.write('        }\n\n\n')

            outfile.close()
            print(pyth_filename, "written.")

        self.shutdown()
        

    def shutdown(self):
        self.running = False
        if self.thread:
            print('shutting down js thread')
            self.thread.join()
            self.thread = None
        print("done")

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='createjs', usage='%(prog)s [options]')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        try:
            self.create_joystick(args)
        except KeyboardInterrupt:
            self.shutdown()

def execute_from_command_line():
    """
    This is the fuction linked to the "donkey" terminal command.
    """
    commands = {
            'createcar': CreateCar,
            'findcar': FindCar,
            'calibrate': CalibrateCar,
            'tubclean': TubManager,
            'tubhist': ShowHistogram,
            'tubplot': ShowPredictionPlots,
            'tubcheck': TubCheck,
            'makemovie': MakeMovie,
            'sim': Sim,
            'createjs': CreateJoystick,
            'consync': ConSync,
            'contrain': ConTrain,
                }
    
    args = sys.argv[:]

    if len(args) > 1 and args[1] in commands.keys():
        command = commands[args[1]]
        c = command()
        c.run(args[2:])
    else:
        dk.utils.eprint('Usage: The availible commands are:')
        dk.utils.eprint(list(commands.keys()))
        
    
    
