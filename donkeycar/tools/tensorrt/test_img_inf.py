"""
Test tensorrt model from onnx 
Usage:
  test_img_inf.py (--trtmodel <trtfile>) (--imgfile <imgfile>) (--conf <conffile>)

  # test_img_inf.py --trtmodel model.trt --imgfile img.jpg --conf config.py
"""

import donkeycar as dk
from docopt import docopt

def infer(trtmodel, imgfile, conffile):
    cfg = dk.load_config(config_path=conffile, myconfig="myconfig.py")
    from donkeycar.parts.tensorrt import TensorRTLinear
    kl = TensorRTLinear(cfg=cfg)

    kl.load(model_path=trtmodel)

    from PIL import Image
    import numpy as np

    pic = Image.open(imgfile)
    pix = np.array(pic)
    print(kl.inference(pix))
    

if __name__ == '__main__':
    args = docopt(__doc__)

    infer(args['<trtfile>'],args['<imgfile>'],args['<conffile>'])