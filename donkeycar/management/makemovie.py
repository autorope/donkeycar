import moviepy.editor as mpy
from tensorflow.python.keras import activations
from tensorflow.python.keras import backend as K

try:
    from vis.visualization import visualize_saliency, overlay
    from vis.utils import utils
    from vis.backprop_modifiers import get
    from vis.losses import ActivationMaximization
    from vis.optimizer import Optimizer
except:
    raise Exception("Please install keras-vis: pip install git+https://github.com/autorope/keras-vis.git")

import donkeycar as dk
from donkeycar.parts.tub_v2 import Tub
from donkeycar.utils import *


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

        conf = os.path.expanduser(args.config)
        if not os.path.exists(conf):
            print("No config file at location: %s. Add --config to specify\
                 location or run from dir containing config.py." % conf)
            return

        self.cfg = dk.load_config(conf)

        if args.type is None and args.model is not None:
            args.type = self.cfg.DEFAULT_MODEL_TYPE
            print("Model type not provided. Using default model type from config file")

        if args.salient:
            if args.model is None:
                print("ERR>> salient visualization requires a model. Pass with the --model arg.")
                parser.print_help()

            if args.type not in ['linear', 'categorical']:
                print("Model type {} is not supported. Only linear or categorical is supported for salient visualization".format(args.type))
                parser.print_help()
                return

        self.tub = Tub(args.tub)

        start = args.start
        self.end_index = args.end if args.end != -1 else len(self.tub)
        num_frames = self.end_index - start

        # Move to the correct offset
        self.current = 0
        self.iterator = self.tub.__iter__()
        while self.current < start:
            self.iterator.next()
            self.current += 1

        self.scale = args.scale
        self.keras_part = None
        self.do_salient = False
        self.user = args.draw_user_input
        if args.model is not None:
            self.keras_part = get_model_by_type(args.type, cfg=self.cfg)
            self.keras_part.load(args.model)
            if args.salient:
                self.do_salient = self.init_salient(self.keras_part.model)

        print('making movie', args.out, 'from', num_frames, 'images')
        clip = mpy.VideoClip(self.make_frame, duration=((num_frames - 1) / self.cfg.DRIVE_LOOP_HZ))
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
        
    def draw_model_prediction(self, img):
        """
        query the model for it's prediction, draw the predictions
        as a blue line on the image
        """
        if self.keras_part is None:
            return

        import cv2

        expected = tuple(self.keras_part.get_input_shape()[1:])
        actual = img.shape

        # if model expects grey-scale but got rgb, covert
        if expected[2] == 1 and actual[2] == 3:
            # normalize image before grey conversion
            grey_img = rgb2gray(img)
            actual = grey_img.shape
            img = grey_img.reshape(grey_img.shape + (1,))

        if expected != actual:
            print("expected input dim", expected, "didn't match actual dim", actual)
            return

        pilot_angle, pilot_throttle = self.keras_part.run(img)
        height, width, _ = img.shape

        length = height
        a2 = pilot_angle * 45.0
        l2 = pilot_throttle * length

        mid = width // 2 - 1

        p2 = tuple((mid + 2, height - 1))
        p22 = tuple((int(p2[0] + l2 * math.cos((a2 + 270.0) * self.deg_to_rad)),
                     int(p2[1] + l2 * math.sin((a2 + 270.0) * self.deg_to_rad))))

        # user is green, pilot is blue
        cv2.line(img, p2, p22, (0, 0, 255), 2)

    def draw_steering_distribution(self, img):
        '''
        query the model for it's prediction, draw the distribution of steering choices
        '''
        from donkeycar.parts.keras import KerasCategorical

        if self.keras_part is None or type(self.keras_part) is not KerasCategorical:
            return

        import cv2

        pred_img = normalize_image(img)
        pred_img = pred_img.reshape((1,) + pred_img.shape)
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
                layer_idx = i

        if first_output_name is None:
            print("Failed to find the model layer named with 'out'. Skipping salient.")
            return False

        print("####################")
        print("Visualizing activations on layer:", first_output_name)
        print("####################")
        
        # ensure we have linear activation
        model.layers[layer_idx].activation = activations.linear
        # build salient model and optimizer
        sal_model = utils.apply_modifications(model)
        modifier_fn = get('guided')
        sal_model_mod = modifier_fn(sal_model)
        losses = [
            (ActivationMaximization(sal_model_mod.layers[layer_idx], None), -1)
        ]
        self.opt = Optimizer(sal_model_mod.input, losses, norm_grads=False)
        return True

    def compute_visualisation_mask(self, img):
        grad_modifier = 'absolute'
        grads = self.opt.minimize(seed_input=img, max_iter=1, grad_modifier=grad_modifier, verbose=False)[1]
        channel_idx = 1 if K.image_data_format() == 'channels_first' else -1
        grads = np.max(grads, axis=channel_idx)
        res = utils.normalize(grads)[0]
        return res

    def draw_salient(self, img):
        import cv2
        alpha = 0.004
        beta = 1.0 - alpha
        expected = self.keras_part.model.inputs[0].shape[1:]
        actual = img.shape

        # check input depth and convert to grey to match expected model input
        if expected[2] == 1 and actual[2] == 3:
            grey_img = rgb2gray(img)
            img = grey_img.reshape(grey_img.shape + (1,))

        norm_img = normalize_image(img)
        salient_mask = self.compute_visualisation_mask(norm_img)
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

        if self.current >= self.end_index:
            return None

        rec = self.iterator.next()
        img_path = os.path.join(self.tub.images_base_path, rec['cam/image_array'])
        image = img_to_arr(Image.open(img_path))

        if self.do_salient:
            image = self.draw_salient(image)
            image = image * 255
            image = image.astype('uint8')
        
        if self.user: self.draw_user_input(rec, image)
        if self.keras_part is not None:
            self.draw_model_prediction(image)
            self.draw_steering_distribution(image)

        if self.scale != 1:
            import cv2
            h, w, d = image.shape
            dsize = (w * self.scale, h * self.scale)
            image = cv2.resize(image, dsize=dsize, interpolation=cv2.INTER_CUBIC)

        self.current += 1
        # returns a 8-bit RGB array
        return image
