import argparse
import os
import shutil
import socket
import stat
import sys
from socket import *
import logging

from progress.bar import IncrementalBar
import donkeycar as dk
from donkeycar.management.joystick_creator import CreateJoystick
from donkeycar.management.tub import TubManager
from donkeycar.pipeline.types import TubDataset
from donkeycar.utils import *

PACKAGE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_PATH = os.path.join(PACKAGE_PATH, 'templates')
HELP_CONFIG = 'location of config file to use. default: ./config.py'
logger = logging.getLogger(__name__)


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
  
    def create_car(self, path, template='complete', overwrite=False):
        """
        This script sets up the folder structure for donkey to work.
        It must run without donkey installed so that people installing with
        docker can build the folder structure for docker to mount to.
        """

        # these are neeeded incase None is passed as path
        path = path or '~/mycar'
        template = template or 'complete'
        print("Creating car folder: {}".format(path))
        path = make_dir(path)
        
        print("Creating data & model folders.")
        folders = ['models', 'data', 'logs']
        folder_paths = [os.path.join(path, f) for f in folders]   
        for fp in folder_paths:
            make_dir(fp)
            
        # add car application and config files if they don't exist
        app_template_path = os.path.join(TEMPLATES_PATH, template+'.py')
        config_template_path = os.path.join(TEMPLATES_PATH, 'cfg_' + template + '.py')
        myconfig_template_path = os.path.join(TEMPLATES_PATH, 'myconfig.py')
        train_template_path = os.path.join(TEMPLATES_PATH, 'train.py')
        calibrate_template_path = os.path.join(TEMPLATES_PATH, 'calibrate.py')
        car_app_path = os.path.join(path, 'manage.py')
        car_config_path = os.path.join(path, 'config.py')
        mycar_config_path = os.path.join(path, 'myconfig.py')
        train_app_path = os.path.join(path, 'train.py')
        calibrate_app_path = os.path.join(path, 'calibrate.py')
        
        if os.path.exists(car_app_path) and not overwrite:
            print('Car app already exists. Delete it and rerun createcar to replace.')
        else:
            print("Copying car application template: {}".format(template))
            shutil.copyfile(app_template_path, car_app_path)
            os.chmod(car_app_path, stat.S_IRWXU)

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
            os.chmod(train_app_path, stat.S_IRWXU)

        if os.path.exists(calibrate_app_path) and not overwrite:
            print('Calibrate already exists. Delete it and rerun createcar to replace.')
        else:
            print("Copying calibrate script. Adjust these before starting your car.")
            shutil.copyfile(calibrate_template_path, calibrate_app_path)
            os.chmod(calibrate_app_path, stat.S_IRWXU)

        if not os.path.exists(mycar_config_path):
            print("Copying my car config overrides")
            shutil.copyfile(myconfig_template_path, mycar_config_path)
            # now copy file contents from config to myconfig, with all lines
            # commented out.
            cfg = open(car_config_path, "rt")
            mcfg = open(mycar_config_path, "at")
            copy = False
            for line in cfg:
                if "import os" in line:
                    copy = True
                if copy: 
                    mcfg.write("# " + line)
            cfg.close()
            mcfg.close()
 
        print("Donkey setup complete.")


class UpdateCar(BaseCommand):
    '''
    always run in the base ~/mycar dir to get latest
    '''

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='update', usage='%(prog)s [options]')
        parser.add_argument('--template', default=None, help='name of car template to use')
        parsed_args = parser.parse_args(args)
        return parsed_args
        
    def run(self, args):
        args = self.parse_args(args)
        cc = CreateCar()
        cc.create_car(path=".", overwrite=True, template=args.template)
        

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
        cmdRPi4 = "sudo nmap -sP " + ip + "/24 | awk '/^Nmap/{ip=$NF}/DC:A6:32/{print ip}'"
        print("Your car's ip address is:" )
        os.system(cmd)
        os.system(cmdRPi4)


class CalibrateCar(BaseCommand):    
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='calibrate', usage='%(prog)s [options]')
        parser.add_argument('--channel', help="The channel you'd like to calibrate [0-15]")
        parser.add_argument('--address', default='0x40', help="The i2c address you'd like to calibrate [default 0x40]")
        parser.add_argument('--bus', default=None, help="The i2c bus you'd like to calibrate [default autodetect]")
        parser.add_argument('--pwmFreq', default=60, help="The frequency to use for the PWM")
        parser.add_argument('--arduino', dest='arduino', action='store_true', help='Use arduino pin for PWM (calibrate pin=<channel>)')
        parser.set_defaults(arduino=False)
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        channel = int(args.channel)

        if args.arduino == True:
            from donkeycar.parts.actuator import ArduinoFirmata

            arduino_controller = ArduinoFirmata(servo_pin=channel)
            print('init Arduino PWM on pin %d' %(channel))
            input_prompt = "Enter a PWM setting to test ('q' for quit) (0-180): "
        else:
            from donkeycar.parts.actuator import PCA9685
            from donkeycar.parts.sombrero import Sombrero

            s = Sombrero()

            busnum = None
            if args.bus:
                busnum = int(args.bus)
            address = int(args.address, 16)
            print('init PCA9685 on channel %d address %s bus %s' %(channel, str(hex(address)), str(busnum)))
            freq = int(args.pwmFreq)
            print("Using PWM freq: {}".format(freq))
            c = PCA9685(channel, address=address, busnum=busnum, frequency=freq)
            input_prompt = "Enter a PWM setting to test ('q' for quit) (0-1500): "
            print()
        while True:
            try:
                val = input(input_prompt)
                if val == 'q' or val == 'Q':
                    break
                pmw = int(val)
                if args.arduino == True:
                    arduino_controller.set_pulse(channel,pmw)
                else:
                    c.run(pmw)
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt received, exit.")
                break
            except Exception as ex:
                print("Oops, {}".format(ex))


class MakeMovieShell(BaseCommand):
    '''
    take the make movie args and then call make movie command
    with lazy imports
    '''
    def __init__(self):
        self.deg_to_rad = math.pi / 180.0

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='makemovie')
        parser.add_argument('--tub', help='The tub to make movie from')
        parser.add_argument('--out', default='tub_movie.mp4', help='The movie filename to create. default: tub_movie.mp4')
        parser.add_argument('--config', default='./config.py', help=HELP_CONFIG)
        parser.add_argument('--model', default=None, help='the model to use to show control outputs')
        parser.add_argument('--type', default=None, required=False, help='the model type to load')
        parser.add_argument('--salient', action="store_true", help='should we overlay salient map showing activations')
        parser.add_argument('--start', type=int, default=0, help='first frame to process')
        parser.add_argument('--end', type=int, default=-1, help='last frame to process')
        parser.add_argument('--scale', type=int, default=2, help='make image frame output larger by X mult')
        parser.add_argument('--draw-user-input', default=True, action='store_false', help='show user input on the video')
        parsed_args = parser.parse_args(args)
        return parsed_args, parser

    def run(self, args):
        '''
        Load the images from a tub and create a movie from them.
        Movie
        '''
        args, parser = self.parse_args(args)

        from donkeycar.management.makemovie import MakeMovie

        mm = MakeMovie()
        mm.run(args, parser)


class ShowHistogram(BaseCommand):

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='tubhist',
                                         usage='%(prog)s [options]')
        parser.add_argument('--tub', nargs='+', help='paths to tubs')
        parser.add_argument('--record', default=None,
                            help='name of record to create histogram')
        parser.add_argument('--out', default=None,
                            help='path where to save histogram end with .png')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def show_histogram(self, tub_paths, record_name, out):
        """
        Produce a histogram of record type frequency in the given tub
        """
        import pandas as pd
        from matplotlib import pyplot as plt
        from donkeycar.parts.tub_v2 import Tub

        output = out or os.path.basename(tub_paths)
        path_list = tub_paths.split(",")
        records = [record for path in path_list for record
                   in Tub(path, read_only=True)]
        df = pd.DataFrame(records)
        df.drop(columns=["_index", "_timestamp_ms"], inplace=True)
        # this prints it to screen
        if record_name is not None:
            df[record_name].hist(bins=50)
        else:
            df.hist(bins=50)

        try:
            if out is not None:
                filename = output
            else:
                if record_name is not None:
                    filename = f"{output}_hist_{record_name.replace('/', '_')}.png"
                else:
                    filename = f"{output}_hist.png"
            plt.savefig(filename)
            logger.info(f'saving image to: {filename}')
        except Exception as e:
            logger.error(str(e))
        plt.show()

    def run(self, args):
        args = self.parse_args(args)
        if isinstance(args.tub, list):
            args.tub = ','.join(args.tub)
        self.show_histogram(args.tub, args.record, args.out)


class ShowCnnActivations(BaseCommand):

    def __init__(self):
        import matplotlib.pyplot as plt
        self.plt = plt

    def get_activations(self, image_path, model_path, cfg):
        '''
        Extracts features from an image

        returns activations/features
        '''
        from tensorflow.python.keras.models import load_model, Model

        model_path = os.path.expanduser(model_path)
        image_path = os.path.expanduser(image_path)

        model = load_model(model_path, compile=False)
        image = load_image(image_path, cfg)[None, ...]

        conv_layer_names = self.get_conv_layers(model)
        input_layer = model.get_layer(name='img_in').input
        activations = []      
        for conv_layer_name in conv_layer_names:
            output_layer = model.get_layer(name=conv_layer_name).output

            layer_model = Model(inputs=[input_layer], outputs=[output_layer])
            activations.append(layer_model.predict(image)[0])
        return activations

    def create_figure(self, activations):
        import math
        cols = 6

        for i, layer in enumerate(activations):
            fig = self.plt.figure()
            fig.suptitle('Layer {}'.format(i+1))

            print('layer {} shape: {}'.format(i+1, layer.shape))
            feature_maps = layer.shape[2]
            rows = math.ceil(feature_maps / cols)

            for j in range(feature_maps):
                self.plt.subplot(rows, cols, j + 1)

                self.plt.imshow(layer[:, :, j])
        
        self.plt.show()

    def get_conv_layers(self, model):
        conv_layers = []
        for layer in model.layers:
            if layer.__class__.__name__ == 'Conv2D':
                conv_layers.append(layer.name)
        return conv_layers

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='cnnactivations', usage='%(prog)s [options]')
        parser.add_argument('--image', help='path to image')
        parser.add_argument('--model', default=None, help='path to model')
        parser.add_argument('--config', default='./config.py', help=HELP_CONFIG)
        
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        cfg = load_config(args.config)
        activations = self.get_activations(args.image, args.model, cfg)
        self.create_figure(activations)


class ShowPredictionPlots(BaseCommand):

    def plot_predictions(self, cfg, tub_paths, model_path, limit, model_type):
        """
        Plot model predictions for angle and throttle against data from tubs.
        """
        import matplotlib.pyplot as plt
        import pandas as pd
        from pathlib import Path

        model_path = os.path.expanduser(model_path)
        model = dk.utils.get_model_by_type(model_type, cfg)
        # This just gets us the text for the plot title:
        if model_type is None:
            model_type = cfg.DEFAULT_MODEL_TYPE
        model.load(model_path)

        user_angles = []
        user_throttles = []
        pilot_angles = []
        pilot_throttles = []       

        base_path = Path(os.path.expanduser(tub_paths)).absolute().as_posix()
        dataset = TubDataset(config=cfg, tub_paths=[base_path],
                             seq_size=model.seq_size())
        records = dataset.get_records()[:limit]
        bar = IncrementalBar('Inferencing', max=len(records))

        for tub_record in records:
            inputs = model.x_transform_and_process(
                tub_record, lambda x: normalize_image(x))
            input_dict = model.x_translate(inputs)
            pilot_angle, pilot_throttle = \
                model.inference_from_dict(input_dict)
            user_angle, user_throttle = model.y_transform(tub_record)
            user_angles.append(user_angle)
            user_throttles.append(user_throttle)
            pilot_angles.append(pilot_angle)
            pilot_throttles.append(pilot_throttle)
            bar.next()

        angles_df = pd.DataFrame({'user_angle': user_angles,
                                  'pilot_angle': pilot_angles})
        throttles_df = pd.DataFrame({'user_throttle': user_throttles,
                                     'pilot_throttle': pilot_throttles})

        fig = plt.figure()
        title = f"Model Predictions\nTubs: {tub_paths}\nModel: {model_path}\n" \
                f"Type: {model_type}"
        fig.suptitle(title)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        angles_df.plot(ax=ax1)
        throttles_df.plot(ax=ax2)
        ax1.legend(loc=4)
        ax2.legend(loc=4)
        plt.savefig(model_path + '_pred.png')
        logger.info(f'Saving model at {model_path}_pred.png')
        plt.show()

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='tubplot', usage='%(prog)s [options]')
        parser.add_argument('--tub', nargs='+', help='The tub to make plot from')
        parser.add_argument('--model', default=None, help='model for predictions')
        parser.add_argument('--limit', type=int, default=1000, help='how many records to process')
        parser.add_argument('--type', default=None, help='model type')
        parser.add_argument('--config', default='./config.py', help=HELP_CONFIG)
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        args.tub = ','.join(args.tub)
        cfg = load_config(args.config)
        self.plot_predictions(cfg, args.tub, args.model, args.limit, args.type)


class Train(BaseCommand):

    def parse_args(self, args):
        HELP_FRAMEWORK = 'the AI framework to use (tensorflow|pytorch). ' \
                         'Defaults to config.DEFAULT_AI_FRAMEWORK'
        parser = argparse.ArgumentParser(prog='train', usage='%(prog)s [options]')
        parser.add_argument('--tub', nargs='+', help='tub data for training')
        parser.add_argument('--model', default=None, help='output model name')
        parser.add_argument('--type', default=None, help='model type')
        parser.add_argument('--config', default='./config.py', help=HELP_CONFIG)
        parser.add_argument('--framework',
                            choices=['tensorflow', 'pytorch', None],
                            required=False,
                            help=HELP_FRAMEWORK)
        parser.add_argument('--checkpoint', type=str,
                            help='location of checkpoint to resume training from')
        parser.add_argument('--transfer', type=str, help='transfer model')
        parser.add_argument('--comment', type=str,
                            help='comment added to model database - use '
                                 'double quotes for multiple words')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        args.tub = ','.join(args.tub)
        cfg = load_config(args.config)
        framework = args.framework if args.framework \
            else getattr(cfg, 'DEFAULT_AI_FRAMEWORK', 'tensorflow')

        if framework == 'tensorflow':
            from donkeycar.pipeline.training import train
            train(cfg, args.tub, args.model, args.type, args.transfer,
                  args.comment)
        elif framework == 'pytorch':
            from donkeycar.parts.pytorch.torch_train import train
            train(cfg, args.tub, args.model, args.type,
                  checkpoint_path=args.checkpoint)
        else:
            print(f"Unrecognized framework: {framework}. Please specify one of "
                  f"'tensorflow' or 'pytorch'")


class ModelDatabase(BaseCommand):

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='models',
                                         usage='%(prog)s [options]')
        parser.add_argument('--config', default='./config.py', help=HELP_CONFIG)
        parser.add_argument('--group', action="store_true",
                            default=False,
                            help='group tubs and plot separately')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        from donkeycar.pipeline.database import PilotDatabase
        args = self.parse_args(args)
        cfg = load_config(args.config)
        p = PilotDatabase(cfg)
        pilot_txt, tub_txt, _ = p.pretty_print(args.group)
        print(pilot_txt)
        print(tub_txt)


class Gui(BaseCommand):
    def run(self, args):
        from donkeycar.management.kivy_ui import main
        main()


def execute_from_command_line():
    """
    This is the function linked to the "donkey" terminal command.
    """
    commands = {
        'createcar': CreateCar,
        'findcar': FindCar,
        'calibrate': CalibrateCar,
        'tubclean': TubManager,
        'tubplot': ShowPredictionPlots,
        'tubhist': ShowHistogram,
        'makemovie': MakeMovieShell,
        'createjs': CreateJoystick,
        'cnnactivations': ShowCnnActivations,
        'update': UpdateCar,
        'train': Train,
        'models': ModelDatabase,
        'ui': Gui,
    }
    
    args = sys.argv[:]

    if len(args) > 1 and args[1] in commands.keys():
        command = commands[args[1]]
        c = command()
        c.run(args[2:])
    else:
        dk.utils.eprint('Usage: The available commands are:')
        dk.utils.eprint(list(commands.keys()))

    
if __name__ == "__main__":
    execute_from_command_line()
