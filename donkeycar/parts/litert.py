from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import Dict, Tuple, Union, List, Sequence, Callable

import numpy as np

import donkeycar as dk
from donkeycar.utils import normalize_image, linear_bin
from donkeycar.pipeline.types import TubRecord
from donkeycar.parts.interpreter import Interpreter, TfLite


class LiteRTPilot(ABC):
    """
    Lightweight pilot interface for TensorFlow Lite Runtime only
    environments. Mirrors the runtime behavior of the Keras pilots without
    importing TensorFlow.
    """

    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
    ) -> None:
        self.input_shape = input_shape
        self.interpreter = interpreter or TfLite()
        self.interpreter.set_model(self)

    def load(self, model_path: str) -> None:
        self.interpreter.load(model_path)

    def shutdown(self) -> None:
        pass

    def compile(self) -> None:
        pass

    def seq_size(self) -> int:
        return 0

    def run(self, img_arr: np.ndarray, *other_arr: List[float]) \
            -> Tuple[Union[float, np.ndarray], ...]:
        norm_img_arr = normalize_image(img_arr)
        np_other_array = tuple(np.array(arr) for arr in other_arr)
        input_dict = self.build_input_dict(norm_img_arr, np_other_array)
        return self.inference_from_dict(input_dict)

    def inference_from_dict(self, input_dict: Dict[str, np.ndarray]) \
            -> Tuple[Union[float, np.ndarray], ...]:
        output = self.interpreter.predict_from_dict(input_dict)
        return self.interpreter_to_output(output)

    @abstractmethod
    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        pass

    @abstractmethod
    def interpreter_to_output(
            self,
            interpreter_out: Sequence[Union[float, np.ndarray]]) \
            -> Tuple[Union[float, np.ndarray], ...]:
        pass


class LiteRTCategorical(LiteRTPilot):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        throttle_range: float = 0.5,
    ) -> None:
        self.throttle_range = throttle_range
        super().__init__(interpreter, input_shape)

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        return {'img_in': norm_img_arr}

    def interpreter_to_output(self, interpreter_out):
        angle_binned, throttle_binned = interpreter_out
        N = len(throttle_binned)
        throttle = dk.utils.linear_unbin(throttle_binned, N=N,
                                         offset=0.0, R=self.throttle_range)
        angle = dk.utils.linear_unbin(angle_binned)
        return angle, throttle

    def y_transform(self, record: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(record, TubRecord), "TubRecord expected"
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        angle = linear_bin(angle, N=15, offset=1, R=2.0)
        throttle = linear_bin(throttle, N=20, offset=0.0, R=self.throttle_range)
        return {'angle_out': angle, 'throttle_out': throttle}


class LiteRTLinear(LiteRTPilot):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        num_outputs: int = 2,
    ) -> None:
        self.num_outputs = num_outputs
        super().__init__(interpreter, input_shape)

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        return {'img_in': norm_img_arr}

    def interpreter_to_output(self, interpreter_out):
        steering = interpreter_out[0]
        if self.num_outputs == 1:
            return steering, dk.utils.throttle(steering)
        throttle = interpreter_out[1]
        return steering[0], throttle[0]


class LiteRTMemory(LiteRTLinear):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        mem_length: int = 3,
        mem_depth: int = 0,
        mem_start_speed: float = 0.0,
        **kwargs,
    ):
        self.mem_length = mem_length
        self.mem_start_speed = mem_start_speed
        self.mem_depth = mem_depth
        self.mem_seq = deque([[0.0, mem_start_speed]] * mem_length)
        super().__init__(interpreter, input_shape, **kwargs)

    def seq_size(self) -> int:
        return self.mem_length + 1

    def load(self, model_path: str) -> None:
        super().load(model_path)
        mem_shape = self.interpreter.get_input_shape('mem_in')
        self.mem_length = mem_shape[1] // 2
        self.mem_seq = deque([[0.0, self.mem_start_speed]] * self.mem_length)

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        np_mem_arr = np.array(self.mem_seq).reshape((2 * self.mem_length,))
        return {'img_in': norm_img_arr, 'mem_in': np_mem_arr}

    def run(self, img_arr: np.ndarray, *other_arr: List[float]) \
            -> Tuple[Union[float, np.ndarray], ...]:
        values = super().run(img_arr, *other_arr)
        angle, throttle = values
        self.mem_seq.popleft()
        self.mem_seq.append([angle, throttle])
        return values

    def y_transform(self, records: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(records, list), 'List[TubRecord] expected'
        angle = records[-1].underlying['user/angle']
        throttle = records[-1].underlying['user/throttle']
        return {'n_outputs0': angle, 'n_outputs1': throttle}


class LiteRTInferred(LiteRTLinear):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
    ) -> None:
        super().__init__(interpreter, input_shape, num_outputs=1)

    def interpreter_to_output(self, interpreter_out):
        steering = interpreter_out[0]
        return steering, dk.utils.throttle(steering)

    def y_transform(self, record: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(record, TubRecord), "TubRecord expected"
        angle: float = record.underlying['user/angle']
        return {'n_outputs0': angle}


class LiteRTIMU(LiteRTPilot):
    imu_vec = [f'imu/{f}_{x}' for f in ('acl', 'gyr') for x in 'xyz']

    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        num_outputs: int = 2,
    ) -> None:
        self.num_outputs = num_outputs
        super().__init__(interpreter, input_shape)

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        imu_arr = other_arr[0] if other_arr else np.array([])
        return {'img_in': norm_img_arr, 'imu_in': imu_arr}

    def interpreter_to_output(self, interpreter_out) \
            -> Tuple[Union[float, np.ndarray], ...]:
        steering = interpreter_out[0]
        throttle = interpreter_out[1]
        return steering[0], throttle[0]

    def x_transform(
            self,
            record: Union[TubRecord, List[TubRecord]],
            img_processor: Callable[[np.ndarray], np.ndarray]) \
            -> Dict[str, Union[float, np.ndarray]]:
        assert isinstance(record, TubRecord), 'TubRecord expected'
        img_arr = record.image(processor=img_processor)
        imu_arr = np.array([record.underlying[k] for k in self.imu_vec])
        return {'img_in': img_arr, 'imu_in': imu_arr}

    def y_transform(self, record: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(record, TubRecord), 'TubRecord expected'
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        return {'n_outputs0': angle, 'n_outputs1': throttle}


class LiteRTBehavioral(LiteRTCategorical):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        throttle_range: float = 0.5,
        num_behavior_inputs: int = 0,
    ) -> None:
        self.num_behavior_inputs = num_behavior_inputs
        super().__init__(interpreter, input_shape, throttle_range)

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        behavior_arr = other_arr[0] if other_arr else np.array([])
        return {'img_in': norm_img_arr, 'xbehavior_in': behavior_arr}

    def y_transform(self, record: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(record, TubRecord), "TubRecord expected"
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        angle = linear_bin(angle, N=15, offset=1, R=2.0)
        throttle = linear_bin(throttle, N=20, offset=0.0,
                              R=self.throttle_range)
        bhv = record.underlying['behavior/state_array']
        return {'angle_out': angle, 'throttle_out': throttle,
                'xbehavior_in': np.array(bhv)}


class LiteRTLocalizer(LiteRTPilot):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        num_locations: int = 10,
    ) -> None:
        self.num_locations = num_locations
        super().__init__(interpreter, input_shape)

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        return {'img_in': norm_img_arr}

    def interpreter_to_output(self, interpreter_out) \
            -> Tuple[Union[float, np.ndarray], ...]:
        angle = interpreter_out[0]
        throttle = interpreter_out[1]
        loc = np.argmax(interpreter_out[2])
        return angle[0], throttle[0], loc

    def y_transform(self, record: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(record, TubRecord), "TubRecord expected"
        angle: float = record.underlying['user/angle']
        throttle: float = record.underlying['user/throttle']
        loc = record.underlying['localizer/location']
        loc_one_hot = np.zeros(self.num_locations)
        loc_one_hot[loc] = 1
        return {'angle': angle, 'throttle': throttle, 'zloc': loc_one_hot}


class LiteRTLSTM(LiteRTPilot):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        seq_length: int = 3,
        num_outputs: int = 2,
    ) -> None:
        self.num_outputs = num_outputs
        self.seq_length = seq_length
        self.img_seq = deque()
        super().__init__(interpreter, input_shape)

    def seq_size(self) -> int:
        return self.seq_length

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        return {'img_in': norm_img_arr}

    def run(self, img_arr, *other_arr):
        if img_arr.shape[2] == 3 and self.input_shape[2] == 1:
            img_arr = dk.utils.rgb2gray(img_arr)

        while len(self.img_seq) < self.seq_length:
            self.img_seq.append(img_arr)

        self.img_seq.popleft()
        self.img_seq.append(img_arr)
        new_shape = (self.seq_length, *self.input_shape)
        img_arr = np.array(self.img_seq).reshape(new_shape)
        img_arr_norm = normalize_image(img_arr)
        input_dict = {'img_in': img_arr_norm}
        return self.inference_from_dict(input_dict)

    def interpreter_to_output(self, interpreter_out) \
            -> Tuple[Union[float, np.ndarray], ...]:
        steering = interpreter_out[0]
        throttle = interpreter_out[1]
        return steering, throttle

    def y_transform(self, records: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(records, list), 'List[TubRecord] expected'
        angle = records[-1].underlying['user/angle']
        throttle = records[-1].underlying['user/throttle']
        return {'model_outputs': [angle, throttle]}


class LiteRT3D_CNN(LiteRTPilot):
    def __init__(
        self,
        interpreter: Interpreter | None = None,
        input_shape: Tuple[int, ...] = (120, 160, 3),
        seq_length: int = 20,
        num_outputs: int = 2,
    ) -> None:
        self.num_outputs = num_outputs
        self.seq_length = seq_length
        self.img_seq = deque()
        super().__init__(interpreter, input_shape)

    def seq_size(self) -> int:
        return self.seq_length

    def build_input_dict(
            self,
            norm_img_arr: np.ndarray,
            other_arr: Tuple[np.ndarray, ...]) -> Dict[str, np.ndarray]:
        return {'img_in': norm_img_arr}

    def run(self, img_arr, *other_arr):
        if img_arr.shape[2] == 3 and self.input_shape[2] == 1:
            img_arr = dk.utils.rgb2gray(img_arr)

        while len(self.img_seq) < self.seq_length:
            self.img_seq.append(img_arr)

        self.img_seq.popleft()
        self.img_seq.append(img_arr)
        new_shape = (self.seq_length, *self.input_shape)
        img_arr = np.array(self.img_seq).reshape(new_shape)
        img_arr_norm = normalize_image(img_arr)
        input_dict = {'img_in': img_arr_norm}
        return self.inference_from_dict(input_dict)

    def interpreter_to_output(self, interpreter_out) \
            -> Tuple[Union[float, np.ndarray], ...]:
        steering = interpreter_out[0]
        throttle = interpreter_out[1]
        return steering, throttle

    def y_transform(self, records: Union[TubRecord, List[TubRecord]]) \
            -> Dict[str, Union[float, List[float]]]:
        assert isinstance(records, list), 'List[TubRecord] expected'
        angle = records[-1].underlying['user/angle']
        throttle = records[-1].underlying['user/throttle']
        return {'outputs': [angle, throttle]}
