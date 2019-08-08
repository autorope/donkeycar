import os
from fastai.vision import *
import torch

class FastAiPilot(object):

    def __init__(self):
        self.learn = None

    def load(self, model_path):
        if torch.cuda.is_available():
            print("using cuda for torch inference")
            defaults.device = torch.device('cuda')
        else:
            print("cuda not available for torch inference")


        path = os.path.dirname(model_path)
        fname = os.path.basename(model_path)
        self.learn = load_learner(path=path, file=fname)

    def run(self, img):
        t = pil2tensor(img, dtype=np.float32) # converts to tensor
        im = Image(t) # Convert to fastAi Image - this class has "apply_tfms"

        pred = self.learn.predict(im)
        steering = float(pred[0].data[0])
        throttle = float(pred[0].data[1])

        return steering, throttle
    