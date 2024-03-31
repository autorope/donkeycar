import os
from abc import ABC, abstractmethod
import logging
import numpy as np
from typing import Union, Sequence, List

import tensorflow as tf
from tensorflow import keras
from tensorflow.python.saved_model import tag_constants, signature_constants
from tensorflow.python.compiler.tensorrt import trt_convert as trt

logger = logging.getLogger(__name__)


def has_trt_support():
    try:
        converter = trt.TrtGraphConverterV2()
        return True
    except RuntimeError as e:
        logger.warning(e)
        return False


def keras_model_to_tflite(in_filename, out_filename, data_gen=None):
    logger.info(f'Convert model {in_filename} to TFLite {out_filename}')
    model = tf.keras.models.load_model(in_filename, compile=False)
    keras_to_tflite(model, out_filename, data_gen)
    logger.info('TFLite conversion done.')


def keras_to_tflite(model, out_filename, data_gen=None):
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS,
                                           tf.lite.OpsSet.SELECT_TF_OPS]
    converter.allow_custom_ops = True
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
            converter.target_spec.supported_ops \
                = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        except:
            pass
        converter.inference_input_type = tf.uint8
        converter.inference_output_type = tf.uint8
        logger.info("using data generator to create int optimized weights for "
                    "Coral TPU")
    tflite_model = converter.convert()
    open(out_filename, "wb").write(tflite_model)


def saved_model_to_tensor_rt(saved_path: str, tensor_rt_path: str) -> bool:
    """ Converts TF SavedModel format into TensorRT for cuda. Note,
        this works also without cuda as all GPU specific magic is handled
        within TF now. """
    logger.info(f'Converting SavedModel {saved_path} to TensorRT'
                f' {tensor_rt_path}')
    try:
        converter = trt.TrtGraphConverterV2(input_saved_model_dir=saved_path)
        converter.convert()
        converter.save(tensor_rt_path)
        logger.info(f'TensorRT conversion done.')
        return True
    except Exception as e:
        logger.error(f'TensorRT conversion failed because: {e}')
        return False


class Interpreter(ABC):
    """ Base class to delegate between Keras, TFLite and TensorRT """
    def __init__(self):
        self.input_keys: list[str] = None
        self.output_keys: list[str] = None
        self.shapes: tuple[dict] = None

    @abstractmethod
    def load(self, model_path: str) -> None:
        pass

    def load_weights(self, model_path: str, by_name: bool = True) -> None:
        raise NotImplementedError('Requires implementation')

    def set_model(self, pilot: 'KerasPilot') -> None:
        """ Some interpreters will need the model"""
        pass

    def set_optimizer(self, optimizer: tf.keras.optimizers.Optimizer) -> None:
        pass

    def compile(self, **kwargs):
        raise NotImplementedError('Requires implementation')

    @abstractmethod
    def get_input_shape(self, input_name) -> tf.TensorShape:
        pass

    def predict(self, img_arr: np.ndarray, *other_arr: np.ndarray) \
            -> Sequence[Union[float, np.ndarray]]:
        """
        This inference interface just converts the inputs into a dictionary
        :param img_arr:    input image array
        :param other_arr:  second input array
        :return:           model output, Iterable over scalar and/or vectors
        """
        input_dict = dict(zip(self.input_keys, (img_arr, *other_arr)))
        return self.predict_from_dict(input_dict)

    def predict_from_dict(self, input_dict) -> Sequence[Union[float, np.ndarray]]:
        pass

    def summary(self) -> str:
        pass

    def __str__(self) -> str:
        """ For printing interpreter """
        return type(self).__name__


class KerasInterpreter(Interpreter):

    def __init__(self):
        super().__init__()
        self.model: tf.keras.Model = None

    def set_model(self, pilot: 'KerasPilot') -> None:
        self.model = pilot.create_model()
        # input_shape and output_shape in keras are unfortunately not a list
        # if there is only a single input / output. So pack them into a list
        # if they are single:
        input_shape = self.model.input_shape
        if type(input_shape) is not list:
            input_shape = [input_shape]
        output_shape = self.model.output_shape
        if type(output_shape) is not list:
            output_shape = [output_shape]

        self.input_keys = self.model.input_names
        self.output_keys = self.model.output_names
        self.shapes = (dict(zip(self.input_keys, input_shape)),
                       dict(zip(self.output_keys, output_shape)))

    def set_optimizer(self, optimizer: tf.keras.optimizers.Optimizer) -> None:
        self.model.optimizer = optimizer

    def get_input_shape(self, input_name) -> tf.TensorShape:
        assert self.model, 'Model not set'
        return self.shapes[0][input_name]

    def compile(self, **kwargs):
        assert self.model, 'Model not set'
        self.model.compile(**kwargs)

    def predict_from_dict(self, input_dict):
        for k, v in input_dict.items():
            input_dict[k] = self.expand_and_convert(v)
        outputs = self.model(input_dict, training=False)
        # for functional models the output here is a list
        if type(outputs) is list:
            # as we invoke the interpreter with a batch size of one we remove
            # the additional dimension here again
            output = [output.numpy().squeeze(axis=0) for output in outputs]
            return output
        # for sequential models the output shape is (1, n) with n = output dim
        else:
            return outputs.numpy().squeeze(axis=0)

    def load(self, model_path: str) -> None:
        logger.info(f'Loading model {model_path}')
        self.model = keras.models.load_model(model_path, compile=False)

    def load_weights(self, model_path: str, by_name: bool = True) -> \
            None:
        assert self.model, 'Model not set'
        self.model.load_weights(model_path, by_name=by_name)

    def summary(self) -> str:
        return self.model.summary()

    @staticmethod
    def expand_and_convert(arr):
        """ Helper function. """
        # expand each input to shape from [x, y, z] to [1, x, y, z] and
        arr_exp = np.expand_dims(arr, axis=0)
        return arr_exp


class FastAIInterpreter(Interpreter):

    def __init__(self):
        super().__init__()
        self.model = None

    def set_model(self, pilot: 'FastAiPilot') -> None:
        self.model = pilot.create_model()

    def set_optimizer(self, optimizer: 'fastai_optimizer') -> None:
        self.model.optimizer = optimizer

    def get_input_shape(self, input_name):
        assert self.model, 'Model not set'
        return self.model.inputs[0].shape

    def compile(self, **kwargs):
        pass

    def invoke(self, inputs):
        outputs = self.model(inputs)
        # for functional models the output here is a list
        if type(outputs) is list:
            # as we invoke the interpreter with a batch size of one we remove
            # the additional dimension here again
            output = [output.numpy().squeeze(axis=0) for output in outputs]
            return output
        # for sequential models the output shape is (1, n) with n = output dim
        else:
            return outputs.detach().numpy().squeeze(axis=0)

    def predict(self, img_arr: np.ndarray, other_arr: np.ndarray) \
            -> Sequence[Union[float, np.ndarray]]:
        import torch
        inputs = torch.unsqueeze(img_arr, 0)
        if other_arr is not None:
            inputs = [img_arr, other_arr]
        return self.invoke(inputs)

    def load(self, model_path: str) -> None:
        import torch
        logger.info(f'Loading model {model_path}')
        if torch.cuda.is_available():
            logger.info("using cuda for torch inference")
            self.model = torch.load(model_path)
        else:
            logger.info("cuda not available for torch inference")
            self.model = torch.load(model_path, map_location=torch.device('cpu'))

        logger.info(self.model)
        self.model.eval()

    def summary(self) -> str:
        return self.model


class TfLite(Interpreter):
    """
    This class wraps around the TensorFlow Lite interpreter.
    """

    def __init__(self):
        super().__init__()
        self.interpreter = None
        self.runner = None
        self.signatures = None
    
    def load(self, model_path):
        assert os.path.splitext(model_path)[1] == '.tflite', \
            'TFlitePilot should load only .tflite files'
        logger.info(f'Loading model {model_path}')
        # Load TFLite model and extract input and output keys
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.signatures = self.interpreter.get_signature_list()
        self.runner = self.interpreter.get_signature_runner()
        self.input_keys = self.signatures['serving_default']['inputs']
        self.output_keys = self.signatures['serving_default']['outputs']

    def compile(self, **kwargs):
        pass

    def predict_from_dict(self, input_dict):
        for k, v in input_dict.items():
            input_dict[k] = self.expand_and_convert(v)
        outputs = self.runner(**input_dict)
        ret = list(outputs[k][0] for k in self.output_keys)
        return ret if len(ret) > 1 else ret[0]

    def get_input_shape(self, input_name):
        assert self.interpreter is not None, "Need to load tflite model first"
        details = self.interpreter.get_input_details()
        for detail in details:
            if detail['name'] == f"serving_default_{input_name}:0":
                return detail['shape']
        raise RuntimeError(f'{input_name} not found in TFlite model')

    @staticmethod
    def expand_and_convert(arr):
        """ Helper function. """
        # expand each input to shape from [x, y, z] to [1, x, y, z] and
        # convert to float32 for expression:
        arr_exp = np.expand_dims(arr, axis=0).astype(np.float32)
        return arr_exp


class TensorRT(Interpreter):
    """
    Uses TensorRT to do the inference.
    """
    def __init__(self):
        super().__init__()
        self.graph_func = None
        self.pilot = None

    def set_model(self, pilot: 'KerasPilot') -> None:
        # We can't determine the output shape neither here, nor in the
        # constructor, because calling output_shapes() on the model will call
        # get_input_shape() from the interpreter which will fail at that
        # state as the trt model hasn't been loaded yet
        self.pilot = pilot

    def get_input_shape(self, input_name) -> tf.TensorShape:
        assert self.graph_func, "Requires loadin the tensorrt model first"
        return self.graph_func.structured_input_signature[1][input_name].shape

    def compile(self, **kwargs):
        pass

    def load(self, model_path: str) -> None:
        logger.info(f'Loading TensorRT model {model_path}')
        assert self.pilot, "Need to set pilot first"
        try:
            ext = os.path.splitext(model_path)[1]
            if ext == '.savedmodel':
                # first load tf model format to extract input and output keys
                model = tf.keras.models.load_model(model_path, compile=False)
                self.input_keys = model.input_names
                self.output_keys = model.output_names
                converter \
                    = trt.TrtGraphConverterV2(input_saved_model_dir=model_path)
                self.graph_func = converter.convert()
            else:
                trt_model_loaded = tf.saved_model.load(
                    model_path, tags=[tag_constants.SERVING])
                self.graph_func = trt_model_loaded.signatures[
                    signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY]
                inputs, outputs = self.pilot.output_shapes()
                self.input_keys = list(inputs.keys())
                self.output_keys = list(outputs.keys())
            logger.info(f'Finished loading TensorRT model.')
        except Exception as e:
            logger.error(f'Could not load TensorRT model because: {e}')

    def predict_from_dict(self, input_dict):
        for k, v in input_dict.items():
            input_dict[k] = self.expand_and_convert(v)
        out_list = self.graph_func(**input_dict)
        # Squeeze here because we send a batch of size one, so pick first
        # element. To return the order of outputs as defined in the model we
        # need to iterate through the model's output shapes here
        outputs = [k.numpy().squeeze(axis=0) for k in out_list]

        # don't return list if output is 1d
        return outputs if len(outputs) > 1 else outputs[0]

    @staticmethod
    def expand_and_convert(arr):
        """ Helper function. """
        # expand each input to shape from [x, y, z] to [1, x, y, z] and
        # convert to float32 for expression:
        arr_exp = np.expand_dims(arr, axis=0)
        return tf.convert_to_tensor(value=arr_exp, dtype=tf.float32)
