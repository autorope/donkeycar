import os
from abc import ABC, abstractmethod
import logging
import numpy as np
from typing import Union, Sequence, List

import tensorflow as tf
from tensorflow import keras

from tensorflow.python.framework.convert_to_constants import \
    convert_variables_to_constants_v2 as convert_var_to_const
from tensorflow.python.saved_model import tag_constants, signature_constants

logger = logging.getLogger(__name__)


def keras_model_to_tflite(in_filename, out_filename, data_gen=None):
    logger.info(f'Convert model {in_filename} to TFLite {out_filename}')
    model = tf.keras.models.load_model(in_filename)
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


def saved_model_to_tensor_rt(saved_path: str, tensor_rt_path: str):
    """ Converts TF SavedModel format into TensorRT for cuda. Note,
        this works also without cuda as all GPU specific magic is handled
        within TF now. """
    logger.info(f'Converting SavedModel {saved_path} to TensorRT'
                f' {tensor_rt_path}')
    from tensorflow.python.compiler.tensorrt import trt_convert as trt

    params = trt.DEFAULT_TRT_CONVERSION_PARAMS
    params = params._replace(max_workspace_size_bytes=(1 << 32))
    params = params._replace(precision_mode="FP16")
    params = params._replace(maximum_cached_engines=100)
    try:
        converter = trt.TrtGraphConverterV2(
            input_saved_model_dir=saved_path,
            conversion_params=params)
        converter.convert()
        converter.save(tensor_rt_path)
        logger.info(f'TensorRT conversion done.')
    except Exception as e:
        logger.error(f'TensorRT conversion failed because: {e}')


class Interpreter(ABC):
    """ Base class to delegate between Keras, TFLite and TensorRT """

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
    def get_input_shapes(self) -> List[tf.TensorShape]:
        pass

    @abstractmethod
    def predict(self, img_arr: np.ndarray, other_arr: np.ndarray) \
            -> Sequence[Union[float, np.ndarray]]:
        pass

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

    def set_optimizer(self, optimizer: tf.keras.optimizers.Optimizer) -> None:
        self.model.optimizer = optimizer

    def get_input_shapes(self) -> List[tf.TensorShape]:
        assert self.model, 'Model not set'
        return [inp.shape for inp in self.model.inputs]

    def compile(self, **kwargs):
        assert self.model, 'Model not set'
        self.model.compile(**kwargs)

    def invoke(self, inputs):
        outputs = self.model(inputs, training=False)
        # for functional models the output here is a list
        if type(outputs) is list:
            # as we invoke the interpreter with a batch size of one we remove
            # the additional dimension here again
            output = [output.numpy().squeeze(axis=0) for output in outputs]
            return output
        # for sequential models the output shape is (1, n) with n = output dim
        else:
            return outputs.numpy().squeeze(axis=0)

    def predict(self, img_arr: np.ndarray, other_arr: np.ndarray) \
            -> Sequence[Union[float, np.ndarray]]:
        img_arr = np.expand_dims(img_arr, axis=0)
        inputs = img_arr
        if other_arr is not None:
            other_arr = np.expand_dims(other_arr, axis=0)
            inputs = [img_arr, other_arr]
        return self.invoke(inputs)

    def predict_from_dict(self, input_dict):
        for k, v in input_dict.items():
            input_dict[k] = np.expand_dims(v, axis=0)
        return self.invoke(input_dict)

    def load(self, model_path: str) -> None:
        logger.info(f'Loading model {model_path}')
        self.model = keras.models.load_model(model_path, compile=False)

    def load_weights(self, model_path: str, by_name: bool = True) -> \
            None:
        assert self.model, 'Model not set'
        self.model.load_weights(model_path, by_name=by_name)

    def summary(self) -> str:
        return self.model.summary()


class FastAIInterpreter(Interpreter):

    def __init__(self):
        super().__init__()
        self.model: None
        from fastai import learner as fastai_learner
        from fastai import optimizer as fastai_optimizer

    def set_model(self, pilot: 'FastAiPilot') -> None:
        self.model = pilot.create_model()

    def set_optimizer(self, optimizer: 'fastai_optimizer') -> None:
        self.model.optimizer = optimizer

    def get_input_shapes(self):
        assert self.model, 'Model not set'
        return [inp.shape for inp in self.model.inputs]

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
            #other_arr = np.expand_dims(other_arr, axis=0)
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
        self.input_shapes = None
        self.input_details = None
        self.output_details = None
    
    def load(self, model_path):
        assert os.path.splitext(model_path)[1] == '.tflite', \
            'TFlitePilot should load only .tflite files'
        logger.info(f'Loading model {model_path}')
        # Load TFLite model and allocate tensors.
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        # Get input and output tensors.
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Get Input shape
        self.input_shapes = []
        logger.info('Load model with tflite input tensor details:')
        for detail in self.input_details:
            logger.debug(detail)
            self.input_shapes.append(detail['shape'])

    def compile(self, **kwargs):
        pass

    def invoke(self) -> Sequence[Union[float, np.ndarray]]:
        self.interpreter.invoke()
        outputs = []
        for tensor in self.output_details:
            output_data = self.interpreter.get_tensor(tensor['index'])
            # as we invoke the interpreter with a batch size of one we remove
            # the additional dimension here again
            outputs.append(output_data[0])
        # don't return list if output is 1d
        return outputs if len(outputs) > 1 else outputs[0]

    def predict(self, img_arr, other_arr) \
            -> Sequence[Union[float, np.ndarray]]:
        assert self.input_shapes and self.input_details, \
            "Tflite model not loaded"
        input_arrays = (img_arr, other_arr)
        for arr, shape, detail \
                in zip(input_arrays, self.input_shapes, self.input_details):
            in_data = arr.reshape(shape).astype(np.float32)
            self.interpreter.set_tensor(detail['index'], in_data)
        return self.invoke()

    def predict_from_dict(self, input_dict):
        for detail in self.input_details:
            k = detail['name']
            inp_k = input_dict[k]
            inp_k_res = inp_k.reshape(detail['shape']).astype(np.float32)
            self.interpreter.set_tensor(detail['index'], inp_k_res)
        return self.invoke()

    def get_input_shapes(self):
        assert self.input_shapes is not None, "Need to load model first"
        return self.input_shapes


class TensorRT(Interpreter):
    """
    Uses TensorRT to do the inference.
    """
    def __init__(self):
        self.frozen_func = None
        self.input_shapes = None

    def get_input_shapes(self) -> List[tf.TensorShape]:
        return self.input_shapes

    def compile(self, **kwargs):
        pass

    def load(self, model_path: str) -> None:
        saved_model_loaded = tf.saved_model.load(model_path,
                                                 tags=[tag_constants.SERVING])
        graph_func = saved_model_loaded.signatures[
            signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY]
        self.frozen_func = convert_var_to_const(graph_func)
        self.input_shapes = [inp.shape for inp in graph_func.inputs]

    def predict(self, img_arr: np.ndarray, other_arr: np.ndarray) \
            -> Sequence[Union[float, np.ndarray]]:
        # first reshape as usual
        img_arr = np.expand_dims(img_arr, axis=0).astype(np.float32)
        img_tensor = self.convert(img_arr)
        if other_arr is not None:
            other_arr = np.expand_dims(other_arr, axis=0).astype(np.float32)
            other_tensor = self.convert(other_arr)
            output_tensors = self.frozen_func(img_tensor, other_tensor)
        else:
            output_tensors = self.frozen_func(img_tensor)

        # because we send a batch of size one, pick first element
        outputs = [out.numpy().squeeze(axis=0) for out in output_tensors]
        # don't return list if output is 1d
        return outputs if len(outputs) > 1 else outputs[0]

    def predict_from_dict(self, input_dict):
        args = []
        for inp in self.frozen_func.inputs:
            name = inp.name.split(':')[0]
            val = input_dict[name]
            val_res = np.expand_dims(val, axis=0).astype(np.float32)
            val_conv = self.convert(val_res)
            args.append(val_conv)
        output_tensors = self.frozen_func(*args)
        # because we send a batch of size one, pick first element
        outputs = [out.numpy().squeeze(axis=0) for out in output_tensors]
        # don't return list if output is 1d
        return outputs if len(outputs) > 1 else outputs[0]

    @staticmethod
    def convert(arr):
        """ Helper function. """
        value = tf.compat.v1.get_variable("features", dtype=tf.float32,
                                          initializer=tf.constant(arr))
        return tf.convert_to_tensor(value=value)
