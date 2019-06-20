
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
from donkeycar.management.tub import TubManager
from donkeycar.management.joystick_creator import CreateJoystick
import numpy as np

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
    
    def create_car(self, path, template='complete', overwrite=False):
        """
        This script sets up the folder structure for donkey to work.
        It must run without donkey installed so that people installing with
        docker can build the folder structure for docker to mount to.
        """

        #these are neeeded incase None is passed as path
        path = path or '~/mycar'
        template = template or 'complete'


        print("Creating car folder: {}".format(path))
        path = make_dir(path)
        
        print("Creating data & model folders.")
        folders = ['models', 'data', 'logs']
        folder_paths = [os.path.join(path, f) for f in folders]   
        for fp in folder_paths:
            make_dir(fp)
            
        #add car application and config files if they don't exist
        app_template_path = os.path.join(TEMPLATES_PATH, template+'.py')
        config_template_path = os.path.join(TEMPLATES_PATH, 'cfg_' + template + '.py')
        myconfig_template_path = os.path.join(TEMPLATES_PATH, 'myconfig.py')
        train_template_path = os.path.join(TEMPLATES_PATH, 'train.py')
        car_app_path = os.path.join(path, 'manage.py')
        car_config_path = os.path.join(path, 'config.py')
        mycar_config_path = os.path.join(path, 'myconfig.py')
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

        if not os.path.exists(mycar_config_path):
            print("Copying my car config overrides")
            shutil.copyfile(myconfig_template_path, mycar_config_path)
            #now copy file contents from config to myconfig, with all lines commented out.
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
        parser.add_argument('--address', default='0x40', help='The i2c address youd like to calibrate [default 0x40]')
        parser.add_argument('--bus', default=None, help='The i2c bus youd like to calibrate [default autodetect]')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        from donkeycar.parts.actuator import PCA9685
        from donkeycar.parts.sombrero import Sombrero

        s = Sombrero()

        args = self.parse_args(args)
        channel = int(args.channel)
        busnum = None
        if args.bus:
            busnum = int(args.bus)
        address = int(args.address, 16)
        print('init PCA9685 on channel %d address %s bus %s' %(channel, str(hex(address)), str(busnum)))
        c = PCA9685(channel, address=address, busnum=busnum)
        
        for i in range(10):
            pmw = int(input('Enter a PWM setting to test(0-1500)'))
            c.run(pmw)


class MakeMovie(BaseCommand):    
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='makemovie')
        parser.add_argument('--tub', help='The tub to make movie from')
        parser.add_argument('--out', default='tub_movie.mp4', help='The movie filename to create. default: tub_movie.mp4')
        parser.add_argument('--config', default='./config.py', help='location of config file to use. default: ./config.py')
        parser.add_argument('--model', default='None', help='the model to use to show control outputs')
        parser.add_argument('--type', help='the model type to load')
        parser.add_argument('--salient', action="store_true", help='should we overlay salient map showing avtivations')
        parser.add_argument('--start', type=int, default=1, help='first frame to process')
        parser.add_argument('--end', type=int, default=-1, help='last frame to process')
        parser.add_argument('--scale', type=int, default=2, help='make image frame output larger by X mult')
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
            print("ERR>> --tub argument missing.")
            parser.print_help()
            return

        if args.type is None:
            print("ERR>> --type argument missing.")
            parser.print_help()
            return

        if args.salient:
            if args.model is None or "None" in args.model:
                print("ERR>> salient visualization requires a model. Pass with the --model arg.")
                parser.print_help()
                return

            #imported like this, we make TF conditional on use of --salient
            #and we keep the context maintained throughout our callbacks to 
            #compute the salient mask
            from tensorflow.python.keras import backend as K
            import tensorflow as tf
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  

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
        
        if args.start == 1:
            self.start = self.tub.get_index(shuffled=False)[0]
        else:
            self.start = args.start
        
        if args.end != -1:
            self.end = args.end    
        else:
            self.end = self.num_rec - self.start

        self.num_rec = self.end - self.start
        
        self.iRec = args.start
        self.scale = args.scale
        self.keras_part = None
        self.convolution_part = None
        if not args.model == "None":
            self.keras_part = get_model_by_type(args.type, cfg=cfg)
            self.keras_part.load(args.model)
            self.keras_part.compile()
            if args.salient:
                self.init_salient(self.keras_part.model)

                #This method nested in this way to take the conditional import of TF
                #in a manner that extends to this callback. Done this way, we avoid
                #importing in the below method, which triggers a new cuda device allocation
                #each call.
                def compute_visualisation_mask(img):
                    #from https://github.com/ermolenkodev/keras-salient-object-visualisation
                    
                    activations = self.functor([np.array([img])])
                    activations = [np.reshape(img, (1, img.shape[0], img.shape[1], img.shape[2]))] + activations
                    upscaled_activation = np.ones((3, 6))
                    for layer in [5, 4, 3, 2, 1]:
                        averaged_activation = np.mean(activations[layer], axis=3).squeeze(axis=0) * upscaled_activation
                        output_shape = (activations[layer - 1].shape[1], activations[layer - 1].shape[2])
                        x = tf.constant(
                            np.reshape(averaged_activation, (1,averaged_activation.shape[0],averaged_activation.shape[1],1)),
                            tf.float32
                        )
                        conv = tf.nn.conv2d_transpose(
                            x, self.layers_kernels[layer],
                            output_shape=(1,output_shape[0],output_shape[1], 1), 
                            strides=self.layers_strides[layer], 
                            padding='VALID'
                        )
                        with tf.Session() as session:
                            result = session.run(conv)
                        upscaled_activation = np.reshape(result, output_shape)
                    final_visualisation_mask = upscaled_activation
                    return (final_visualisation_mask - np.min(final_visualisation_mask))/(np.max(final_visualisation_mask) - np.min(final_visualisation_mask))
                self.compute_visualisation_mask = compute_visualisation_mask

        print('making movie', args.out, 'from', self.num_rec, 'images')
        clip = mpy.VideoClip(self.make_frame, duration=(self.num_rec//cfg.DRIVE_LOOP_HZ) - 1)
        clip.write_videofile(args.out,fps=cfg.DRIVE_LOOP_HZ)

        print('done')

    def draw_model_prediction(self, record, img):
        '''
        query the model for it's prediction, draw the user input and the predictions
        as green and blue lines on the image
        '''
        if self.keras_part is None:
            return

        import cv2
         
        user_angle = float(record["user/angle"])
        user_throttle = float(record["user/throttle"])
        expected = self.keras_part.model.inputs[0].shape[1:]
        actual = img.shape
        pred_img = img

        #check input depth
        if expected[2] == 1 and actual[2] == 3:
            pred_img = rgb2gray(pred_img)
            pred_img = pred_img.reshape(pred_img.shape + (1,))
            actual = pred_img.shape

        if(expected != actual):
            print("expected input dim", expected, "didn't match actual dim", actual)
            return

        pilot_angle, pilot_throttle = self.keras_part.run(pred_img)

        a1 = user_angle * 45.0
        l1 = user_throttle * 3.0 * 80.0
        a2 = pilot_angle * 45.0
        l2 = pilot_throttle * 3.0 * 80.0

        p1 = tuple((74, 119))
        p2 = tuple((84, 119))
        p11 = tuple(( int(p1[0] + l1 * math.cos((a1 + 270.0) * math.pi / 180.0)), int(p1[1] + l1 * math.sin((a1 + 270.0) * math.pi / 180.0))))
        p22 = tuple(( int(p2[0] + l2 * math.cos((a2 + 270.0) * math.pi / 180.0)), int(p2[1] + l2 * math.sin((a2 + 270.0) * math.pi / 180.0))))

        cv2.line(img, p1, p11, (0, 255, 0), 2)
        cv2.line(img, p2, p22, (0, 0, 255), 2)

    def draw_steering_distribution(self, record, img):
        '''
        query the model for it's prediction, draw the distribution of steering choices
        '''
        from donkeycar.parts.keras import KerasCategorical

        if self.keras_part is None or type(self.keras_part) is not KerasCategorical:
            return

        import cv2
         
        orig_shape = img.shape
        pred_img = img.reshape((1,) + img.shape)
        angle_binned, throttle = self.keras_part.model.predict(pred_img)
        #img.reshape(orig_shape)

        x = 4
        dx = 4
        y = 120 - 4
        iArgMax = np.argmax(angle_binned)
        for i in range(15):
            p1 = (x, y)
            p2 = (x, y - int(angle_binned[0][i] * 100.0))
            if i == iArgMax:
                cv2.line(img, p1, p2, (255, 0, 0), 2)
            else:
                cv2.line(img, p1, p2, (200, 200, 200), 2)
            x += dx
        

    def init_salient(self, model):
        #from https://github.com/ermolenkodev/keras-salient-object-visualisation
        from tensorflow.python.keras.layers import Input, Dense, merge
        from tensorflow.python.keras.models import Model
        from tensorflow.python.keras.layers import Convolution2D, MaxPooling2D, Reshape, BatchNormalization
        from tensorflow.python.keras.layers import Activation, Dropout, Flatten, Dense

        input_shape = model.inputs[0].shape

        img_in = Input(shape=(input_shape[1], input_shape[2], input_shape[3]), name='img_in')
        x = img_in
        x = Convolution2D(24, (5,5), strides=(2,2), activation='relu', name='conv1')(x)
        x = Convolution2D(32, (5,5), strides=(2,2), activation='relu', name='conv2')(x)
        x = Convolution2D(64, (5,5), strides=(2,2), activation='relu', name='conv3')(x)
        x = Convolution2D(64, (3,3), strides=(2,2), activation='relu', name='conv4')(x)
        conv_5 = Convolution2D(64, (3,3), strides=(1,1), activation='relu', name='conv5')(x)
        self.convolution_part = Model(inputs=[img_in], outputs=[conv_5])

        #print("input model summary:")
        #print(model.summary())
        #print("conv model summary:")
        #print(self.convolution_part.summary())

        for layer_num in ('1', '2', '3', '4', '5'):
            try:
                self.convolution_part.get_layer('conv' + layer_num).set_weights(model.get_layer('conv2d_' + layer_num).get_weights())
            except Exception as e:
                print(e)
                print("Failed to load layer weights for layer", layer_num)
                raise Exception("Failed to load weights")

        from tensorflow.python.keras import backend as K
        import tensorflow as tf
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        
        self.inp = self.convolution_part.input                                           # input placeholder
        self.outputs = [layer.output for layer in self.convolution_part.layers[1:]]          # all layer outputs
        self.functor = K.function([self.inp], self.outputs)

        kernel_3x3 = tf.constant(np.array([
        [[[1]], [[1]], [[1]]], 
        [[[1]], [[1]], [[1]]], 
        [[[1]], [[1]], [[1]]]
        ]), tf.float32)

        kernel_5x5 = tf.constant(np.array([
                [[[1]], [[1]], [[1]], [[1]], [[1]]], 
                [[[1]], [[1]], [[1]], [[1]], [[1]]], 
                [[[1]], [[1]], [[1]], [[1]], [[1]]],
                [[[1]], [[1]], [[1]], [[1]], [[1]]],
                [[[1]], [[1]], [[1]], [[1]], [[1]]]
        ]), tf.float32)

        self.layers_kernels = {5: kernel_3x3, 4: kernel_3x3, 3: kernel_5x5, 2: kernel_5x5, 1: kernel_5x5}

        self.layers_strides = {5: [1, 1, 1, 1], 4: [1, 2, 2, 1], 3: [1, 2, 2, 1], 2: [1, 2, 2, 1], 1: [1, 2, 2, 1]}

        

    def draw_salient(self, img):
        #from https://github.com/ermolenkodev/keras-salient-object-visualisation
        import cv2
        alpha = 0.004
        beta = 1.0 - alpha

        expected = self.keras_part.model.inputs[0].shape[1:]
        actual = img.shape
        pred_img = img

        #check input depth
        if expected[2] == 1 and actual[2] == 3:
            pred_img = rgb2gray(pred_img)
            pred_img = pred_img.reshape(pred_img.shape + (1,))
            actual = pred_img.shape

        salient_mask = self.compute_visualisation_mask(pred_img)
        salient_mask_stacked = np.dstack((salient_mask,salient_mask))
        salient_mask_stacked = np.dstack((salient_mask_stacked,salient_mask))
        blend = cv2.addWeighted(img.astype('float32'), alpha, salient_mask_stacked, beta, 0.0)
        return blend
        

    def make_frame(self, t):
        '''
        Callback to return an image from from our tub records.
        This is called from the VideoClip as it references a time.
        We don't use t to reference the frame, but instead increment
        a frame counter. This assumes sequential access.
        '''
        
        if self.iRec >= self.end:
            return None

        rec = None

        while rec is None and self.iRec < self.end:
            try:
                rec = self.tub.get_record(self.iRec)
            except Exception as e:
                print(e)
                print("Failed to get image for frame", self.iRec)
                self.iRec = self.iRec + 1
                rec = None

        image = rec['cam/image_array']

        if self.convolution_part:
            image = self.draw_salient(image)
            image = image * 255
            image = image.astype('uint8')
        
        self.draw_model_prediction(rec, image)
        self.draw_steering_distribution(rec, image)

        if self.scale != 1:
            import cv2
            h, w, d = image.shape
            dsize = (w * self.scale, h * self.scale)
            image = cv2.resize(image, dsize=dsize, interpolation=cv2.INTER_CUBIC)
        
        self.iRec = self.iRec + 1
        
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
        from donkeycar.parts.keras import KerasCategorical, KerasLinear

        args, parser = self.parse_args(args)

        cfg = load_config(args.config)

        if cfg is None:
            return

        #TODO: this logic should be in a pilot or model handler part.
        if args.type == "categorical":
            kl = KerasCategorical()
        elif args.type == "linear":
            kl = KerasLinear(num_outputs=2)
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

        try:
            filename = os.path.basename(tub_paths) + '_hist_%s.png' % record_name.replace('/', '_')
            plt.savefig(filename)
            print('saving image to:', filename)
        except:
            pass
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


class ShowCnnActivations(BaseCommand):

    def __init__(self):
        import matplotlib.pyplot as plt
        self.plt = plt

    def get_activations(self, image_path, model_path):
        '''
        Extracts features from an image

        returns activations/features
        '''
        from tensorflow.python.keras.models import load_model, Model

        model_path = os.path.expanduser(model_path)
        image_path = os.path.expanduser(image_path)

        model = load_model(model_path)
        image = self.plt.imread(image_path)[None, ...]

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
        
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        activations = self.get_activations(args.image, args.model)
        self.create_figure(activations)


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
        parser.add_argument('--type', default='categorical', help='model type')
        parser.add_argument('--config', default='./config.py', help='location of config file to use. default: ./config.py')
        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        args.tub = ','.join(args.tub)
        cfg = load_config(args.config)
        self.plot_predictions(cfg, args.tub, args.model, args.limit, args.type)
        

def execute_from_command_line():
    """
    This is the function linked to the "donkey" terminal command.
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
            'cnnactivations': ShowCnnActivations,
                }
    
    args = sys.argv[:]

    if len(args) > 1 and args[1] in commands.keys():
        command = commands[args[1]]
        c = command()
        c.run(args[2:])
    else:
        dk.utils.eprint('Usage: The availible commands are:')
        dk.utils.eprint(list(commands.keys()))
        
    
if __name__ == "__main__":
    execute_from_command_line()
    
