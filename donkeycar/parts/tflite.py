import os
import tensorflow as tf
import numpy as np
from typing import Dict, Union

from donkeycar.parts.keras import KerasPilot, KerasLinear, XY


def keras_model_to_tflite(in_filename, out_filename, data_gen=None):
    print('Convert model {:} to TFLite {:}'.format(in_filename, out_filename))
    new_model = tf.keras.models.load_model(in_filename)
    converter = tf.lite.TFLiteConverter.from_keras_model(new_model)
    if data_gen is not None:
        # when we have a data_gen that is the trigger to use it to create
        # integer weights and calibrate them. Warning: this model will no
        # longer run with the standard tflite engine. That uses only float.
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = data_gen
        try:
            converter.target_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        except:
            pass
        try:
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        except:
            pass
        converter.inference_input_type = tf.uint8
        converter.inference_output_type = tf.uint8
        print("using data generator to create int optimized weights for Coral TPU")
    tflite_model = converter.convert()
    open(out_filename, "wb").write(tflite_model)


class TFLitePilot(KerasPilot):
    """
    This class wraps around the TensorFlow Lite interpreter.
    """
    def __init__(self):
        super().__init__()
        self.interpreter = None
        self.input_shape = None
        self.input_details = None
        self.output_details = None
    
    def load(self, model_path):
        assert os.path.splitext(model_path)[1] == '.tflite', \
            'TFlitePilot should load only .tflite files'
        print(f'Loading model {model_path}')
        # Load TFLite model and allocate tensors.
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        # Get input and output tensors.
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Get Input shape
        self.input_shape = self.input_details[0]['shape']
    
    def inference(self, img_arr, other_arr):
        input_data = np.float32(img_arr.reshape(self.input_shape))
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        throttle = 0.0
        outputs = []

        for tensor in self.output_details:
            output_data = self.interpreter.get_tensor(tensor['index'])
            outputs.append(output_data[0][0])

        steering = float(outputs[0])
        if len(outputs) > 1:
            throttle = float(outputs[1])

        return steering, throttle

    def get_input_shape(self):
        assert self.input_shape is not None, "Need to load model first"
        return self.input_shape

    def y_translate(self, y: XY) -> Dict[str, Union[float, np.ndarray]]:
        """ For now only support keras linear"""
        return KerasLinear.y_translate(self, y)
