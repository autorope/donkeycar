import math

import numpy as np
import moviepy.editor as mpy
from tensorflow.python.keras import activations

try:
    from vis.visualization import visualize_saliency, overlay
    from vis.utils import utils
except:
    raise Exception("Please install keras-vis: pip install git+https://github.com/autorope/keras-vis.git")

import donkeycar as dk
from donkeycar.parts.datastore import Tub
from donkeycar.utils import *
from donkeycar.management.tub import TubManager

class MakeMovie(object):
    def __init__(self):
        self.deg_to_rad = math.pi / 180.0

    def run(self, args, parser):
        '''
        Load the images from a tub and create a movie from them.
        Movie
        '''

        if args.tub is None:
            print("ERR>> --tub argument missing.")
            parser.print_help()
            return

        if args.type is None and args.model is not None:
            print("ERR>> --type argument missing. Required when providing a model.")
            parser.print_help()
            return

        if args.salient:
            if args.model is None:
                print("ERR>> salient visualization requires a model. Pass with the --model arg.")
                parser.print_help()

        conf = os.path.expanduser(args.config)

        if not os.path.exists(conf):
            print("No config file at location: %s. Add --config to specify\
                 location or run from dir containing config.py." % conf)
            return

        self.cfg = dk.load_config(conf)
        self.tub = Tub(args.tub)
        self.index = self.tub.get_index(shuffled=False)
        start = args.start
        self.end = args.end if args.end != -1 else len(self.index)
        if self.end >= len(self.index):
            self.end = len(self.index) - 1
        num_frames = self.end - start
        self.iRec = start
        self.scale = args.scale
        self.keras_part = None
        self.do_salient = False
        if args.model is not None:
            self.keras_part = get_model_by_type(args.type, cfg=self.cfg)
            self.keras_part.load(args.model)
            self.keras_part.compile()
            if args.salient:
                self.do_salient = self.init_salient(self.keras_part.model)

        print('making movie', args.out, 'from', num_frames, 'images')
        clip = mpy.VideoClip(self.make_frame,
                             duration=((num_frames - 1) / self.cfg.DRIVE_LOOP_HZ))
        clip.write_videofile(args.out, fps=self.cfg.DRIVE_LOOP_HZ)

    def draw_user_input(self, record, img):
        '''
        Draw the user input as a green line on the image
        '''

        import cv2

        user_angle = float(record["user/angle"])
        user_throttle = float(record["user/throttle"])

        height, width, _ = img.shape

        length = height
        a1 = user_angle * 45.0
        l1 = user_throttle * length

        mid = width // 2 - 1

        p1 = tuple((mid - 2, height - 1))
        p11 = tuple((int(p1[0] + l1 * math.cos((a1 + 270.0) * self.deg_to_rad)),
                     int(p1[1] + l1 * math.sin((a1 + 270.0) * self.deg_to_rad))))

        # user is green, pilot is blue
        cv2.line(img, p1, p11, (0, 255, 0), 2)
        
    def draw_model_prediction(self, record, img):
        '''
        query the model for it's prediction, draw the predictions
        as a blue line on the image
        '''
        if self.keras_part is None:
            return

        import cv2
         
        expected = self.keras_part.model.inputs[0].shape[1:]
        actual = img.shape

        #normalize image before prediction
        pred_img = img.astype(np.float32) / 255.0

        # check input depth
        if expected[2] == 1 and actual[2] == 3:
            pred_img = rgb2gray(pred_img)
            pred_img = pred_img.reshape(pred_img.shape + (1,))
            actual = pred_img.shape

        if expected != actual:
            print("expected input dim", expected, "didn't match actual dim", actual)
            return

        pilot_angle, pilot_throttle = self.keras_part.run(pred_img)
        height, width, _ = pred_img.shape

        length = height
        a2 = pilot_angle * 45.0
        l2 = pilot_throttle * length

        mid = width // 2 - 1

        p2 = tuple((mid + 2, height - 1))
        p22 = tuple((int(p2[0] + l2 * math.cos((a2 + 270.0) * self.deg_to_rad)),
                     int(p2[1] + l2 * math.sin((a2 + 270.0) * self.deg_to_rad))))

        # user is green, pilot is blue
        cv2.line(img, p2, p22, (0, 0, 255), 2)

    def draw_steering_distribution(self, record, img):
        '''
        query the model for it's prediction, draw the distribution of steering choices
        '''
        from donkeycar.parts.keras import KerasCategorical

        if self.keras_part is None or type(self.keras_part) is not KerasCategorical:
            return

        import cv2

        pred_img = img.reshape((1,) + img.shape)
        angle_binned, _ = self.keras_part.model.predict(pred_img)

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
        # Utility to search for layer index by name. 
        # Alternatively we can specify this as -1 since it corresponds to the last layer.
        first_output_name = None
        for i, layer in enumerate(model.layers):
            if first_output_name is None and "dropout" not in layer.name.lower() and "out" in layer.name.lower():
                first_output_name = layer.name
                self.layer_idx = i

        if first_output_name is None:
            print("Failed to find the model layer named with 'out'. Skipping salient.")
            return False

        print("####################")
        print("Visualizing activations on layer:", first_output_name)
        print("####################")
        
        # ensure we have linear activation
        model.layers[self.layer_idx].activation = activations.linear
        self.sal_model = utils.apply_modifications(model)
        return True

    def compute_visualisation_mask(self, img):
        grads = visualize_saliency(self.sal_model, self.layer_idx, filter_indices=None, 
                                   seed_input=img, backprop_modifier='guided')
        return grads

    def draw_salient(self, img):
        import cv2
        alpha = 0.004
        beta = 1.0 - alpha

        expected = self.keras_part.model.inputs[0].shape[1:]
        actual = img.shape
        pred_img = img.astype(np.float32) / 255.0

        # check input depth
        if expected[2] == 1 and actual[2] == 3:
            pred_img = rgb2gray(pred_img)
            pred_img = pred_img.reshape(pred_img.shape + (1,))
            actual = pred_img.shape

        salient_mask = self.compute_visualisation_mask(pred_img)
        z = np.zeros_like(salient_mask)
        salient_mask_stacked = np.dstack((z, z))
        salient_mask_stacked = np.dstack((salient_mask_stacked, salient_mask))
        blend = cv2.addWeighted(img.astype('float32'), alpha, salient_mask_stacked, beta, 0.0)
        return blend

    def make_frame(self, t):
        '''
        Callback to return an image from from our tub records.
        This is called from the VideoClip as it references a time.
        We don't use t to reference the frame, but instead increment
        a frame counter. This assumes sequential access.
        '''

        if self.iRec >= self.end or self.iRec >= len(self.index):
            return None

        rec_ix = self.index[self.iRec]
        rec = self.tub.get_record(rec_ix)
        image = rec['cam/image_array']

        if self.cfg.ROI_CROP_TOP != 0 or self.cfg.ROI_CROP_BOTTOM != 0:
            image = img_crop(image, self.cfg.ROI_CROP_TOP, self.cfg.ROI_CROP_BOTTOM)

        if self.do_salient:
            image = self.draw_salient(image)
            image = image * 255
            image = image.astype('uint8')
        
        self.draw_user_input(rec, image)
        if self.keras_part is not None:
            self.draw_model_prediction(rec, image)
            self.draw_steering_distribution(rec, image)

        if self.scale != 1:
            import cv2
            h, w, d = image.shape
            dsize = (w * self.scale, h * self.scale)
            image = cv2.resize(image, dsize=dsize, interpolation=cv2.INTER_CUBIC)

        self.iRec += 1
        # returns a 8-bit RGB array
        return image
