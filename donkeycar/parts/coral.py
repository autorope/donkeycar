"""Inference Engine used for inference tasks."""

from edgetpu.basic.basic_engine import BasicEngine
import numpy
from PIL import Image


class InferenceEngine(BasicEngine):
  """Engine used for inference task."""

  def __init__(self, model_path, device_path=None):
    """Creates a BasicEngine with given model.

    Args:
      model_path: String, path to TF-Lite Flatbuffer file.
      device_path: String, if specified, bind engine with Edge TPU at device_path.

    Raises:
      ValueError: An error occurred when the output format of model is invalid.
    """
    if device_path:
      super().__init__(model_path, device_path)
    else:
      super().__init__(model_path)
    output_tensors_sizes = self.get_all_output_tensors_sizes()
    if output_tensors_sizes.size > 2:
      raise ValueError(
          ('Inference model should have 2 output tensors or less!'
           'This model has {}.'.format(output_tensors_sizes.size)))

  def Inference(self, img):
    """Inference image with np array image object.

    This interface assumes the loaded model is trained for image
    classification.

    Args:
      img: numpy.array image object.

    Returns:
      List of (float) which represents inference results.

    Raises:
      RuntimeError: when tensor not a single 3 channel image.
      Asserts: when image incorrect size.
    """
    input_tensor_shape = self.get_input_tensor_shape()
    if (input_tensor_shape.size != 4 or input_tensor_shape[3] != 3 or
        input_tensor_shape[0] != 1):
      raise RuntimeError(
          'Invalid input tensor shape! Expected: [1, height, width, 3]')
    _, height, width, _ = input_tensor_shape
    assert(height == img.shape[0])
    assert(width == img.shape[1])
    input_tensor = img.flatten()
    return self.RunInferenceWithInputTensor(input_tensor)

  def RunInferenceWithInputTensor(self, input_tensor):
    """Run inference with raw input tensor.

    This interface requires user to process input data themselves and convert
    it to formatted input tensor.

    Args:
      input_tensor: numpy.array represents the input tensor.

    Returns:
      List of (float) which represents inference.

    Raises:
      ValueError: when input param is invalid.
    """
    _, self._raw_result = self.RunInference(
        input_tensor)
    return [self._raw_result]



class CoralLinearPilot(object):
  '''
  Base class for TFlite models that will provide steering and throttle to guide a car.
  '''
  def __init__(self):
      self.model = None
      self.engine = None

  def load(self, model_path):
      # Load Coral edgetpu TFLite model and allocate tensors.
      self.engine = InferenceEngine(model_path)

  def run(self, image):
      steering, throttle = self.engine.Inference(image)[0]
      return steering, throttle
