"""
Test tensorrt model from onnx 
Usage:
  test_img_inf.py (--trtmodel <rootfile>) (--imgfile <imgfile>) (--conf <conffile>)

  # test_img_inf.py --trtmodel model.trt --imgfile img.jpg --conf config.py
"""

import donkeycar as dk
from docopt import docopt
from PIL import Image
import numpy as np

def infer(modelbase, imgfile, conffile):
    pic = Image.open(imgfile)
    pix = np.array(pic)

    cfg = dk.load_config(config_path=conffile, myconfig="myconfig.py")
    full_onnx_path = modelbase + ".onnx"
    full_trt_path = modelbase + ".trt"

    infer_onnx(full_onnx_path, pix, cfg)
    infer_trt(full_trt_path, pix, cfg)

def infer_onnx(model, img, config):
    from donkeycar.parts.keras import KerasLinear
    from donkeycar.parts.interpreter import OnnxInterpreter
    interpreter = OnnxInterpreter()
    input_shape = (config.IMAGE_H, config.IMAGE_W, config.IMAGE_DEPTH)
    onnx_model = KerasLinear(interpreter=interpreter, input_shape=input_shape, have_odom=config.HAVE_ODOM)
    
    onnx_model.load(model_path=model)
    
    # Pre-processing and inference
    prediction_output = onnx_model.run(img, None)
    print(prediction_output)

    #print(kl.inference(pix))

def infer_trt(model, img, config):
    from donkeycar.parts.tensorrt import TensorRTLinear
    kl = TensorRTLinear(cfg=config)

    kl.load(model_path=model)
    
    # Pre-processing and inference
    prediction_output = kl.run(img)
    print(prediction_output)



if __name__ == '__main__':
    args = docopt(__doc__)

    infer(args['<rootfile>'],args['<imgfile>'],args['<conffile>'])