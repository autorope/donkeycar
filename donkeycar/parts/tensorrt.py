from collections import namedtuple
from donkeycar.parts.keras import KerasPilot
from donkeycar.utils import throttle as calculate_throttle
import json
import numpy as np
import pycuda.driver as cuda
import pycuda.autoinit
from pathlib import Path
import tensorflow as tf
import tensorrt as trt
from donkeycar.tools.tensorrt import engine as eng
import donkeycar as dk

HostDeviceMemory = namedtuple('HostDeviceMemory', 'host_memory device_memory')
ctx = pycuda.autoinit.context
trt.init_libnvinfer_plugins(None, "")
class TensorRTCategorical(KerasPilot):
    '''
    Uses TensorRT to do the inference.
    '''
    def __init__(self, cfg):
        super().__init__()
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.cfg = cfg
        self.engine = None
        self.inputs = None
        self.outputs = None
        self.bindings = None
        self.stream = None
        self.context = None
        self.throttle_range = 0.5
        print(f'inside TensorRTLinear')

    def compile(self):
        print('Nothing to compile')

    def load(self, model_path):
        # uff_model = Path(model_path)
        # metadata_path = Path('%s/%s.metadata'
        #                      % (uff_model.parent.as_posix(), uff_model.stem))
        # with open(metadata_path.as_posix(), 'r') as metadata, \
        #         trt.Builder(self.logger) as builder, \
        #         builder.create_network() as network, \
        #         trt.UffParser() as parser:

        #     builder.max_workspace_size = 1 << 20
        #     builder.max_batch_size = 1
        #     builder.fp16_mode = True

        #     metadata = json.loads(metadata.read())
        #     # Configure inputs and outputs
        #     print('Configuring I/O')
        #     input_names = metadata['input_names']
        #     output_names = metadata['output_names']
        #     for name in input_names:
        #         parser.register_input(name, (self.cfg.TARGET_D,
        #                                      self.cfg.TARGET_H,
        #                                      self.cfg.TARGET_W))

        #     for name in output_names:
        #         parser.register_output(name)
        #     # Parse network
        #     print('Parsing TensorRT Network')
        #     parser.parse(uff_model.as_posix(), network)
        #     print('Building CUDA Engine')
        #     self.engine = builder.build_cuda_engine(network)
        # Allocate buffers
        print("load tensorrt engine")
        self.engine = eng.load_engine(eng.trt_runtime, model_path)
        
        print('Allocating Buffers')
        self.inputs, self.outputs, self.bindings, self.stream \
            = TensorRTCategorical.allocate_buffers(self.engine)
        print("creating context")
        self.context = self.engine.create_execution_context()
        print('Ready')

    def inference(self, image, other_arr=None):
        # Channel first image format
        image = image.transpose((2,0,1)).ravel().astype(np.float32) * 1.0 / 255.0
        
        # image = image.astype(np.float32) * 1.0 / 255.0
        # Flatten it to a 1D array.
        # image = image.ravel()
        # The first input is the image. Copy to host memory.
        image_input = self.inputs[0] 
        np.copyto(image_input.host_memory, image)
        # with self.engine.create_execution_context() as context:
        inference_output = TensorRTCategorical.infer(context=self.context,
                                                bindings=self.bindings,
                                                inputs=self.inputs,
                                                outputs=self.outputs,
                                                stream=self.stream)
        # if len(inference_output) == 2:
            # [throttle, steering] = inference_output
            # print(f"steering={steering} throttle={throttle}")
            # return -0.25, 0.3
            # return steering[0], throttle[0]
            # return steering[0], 0.28
            # angle_binned, throttle_binned = inference_output
            # N = len(throttle_binned[0])
            # throttle = dk.utils.linear_unbin(throttle_binned, N=N,
            #                              offset=0.0, R=self.throttle_range)
            # angle = dk.utils.linear_unbin(angle_binned)
            # return angle, throttle
        # else:
            # [steering] = inference_output
            # print(f"steering={steering}")
            # return steering[0], calculate_throttle(steering[0])

        [angle_binned, throttle_binned] = inference_output
        # N = len(throttle_binned[0])
        # throttle = dk.utils.linear_unbin(throttle_binned, N=N,
        #                                  offset=0.0, R=self.throttle_range)
        # angle = dk.utils.linear_unbin(angle_binned)
        # return angle, throttle

        # [angle_binned] = inference_output
        angle = dk.utils.linear_unbin(angle_binned)
        return angle, 0.35

    @classmethod
    def allocate_buffers(cls, engine):
        inputs = []
        outputs = []
        bindings = []
        stream = cuda.Stream()
        for binding in engine:
            size = trt.volume(engine.get_binding_shape(binding)) \
                   * engine.max_batch_size
            dtype = trt.nptype(engine.get_binding_dtype(binding))
            # Allocate host and device buffers
            host_memory = cuda.pagelocked_empty(size, dtype)
            device_memory = cuda.mem_alloc(host_memory.nbytes)
            bindings.append(int(device_memory))
            if engine.binding_is_input(binding):
                inputs.append(HostDeviceMemory(host_memory, device_memory))
            else:
                outputs.append(HostDeviceMemory(host_memory, device_memory))

        return inputs, outputs, bindings, stream

    @classmethod
    def infer(cls, context, bindings, inputs, outputs, stream, batch_size=1):
        # Transfer input data to the GPU.
        [cuda.memcpy_htod_async(inp.device_memory, inp.host_memory, stream)
         for inp in inputs]
        # Run inference.
        context.execute_async(batch_size=batch_size, bindings=bindings,
                              stream_handle=stream.handle)
        # Transfer predictions back from the GPU.
        [cuda.memcpy_dtoh_async(out.host_memory, out.device_memory, stream)
         for out in outputs]
        # Synchronize the stream
        stream.synchronize()
        # Return only the host outputs.
        return [out.host_memory for out in outputs]


class TensorRTLinear(KerasPilot):
    '''
    Uses TensorRT to do the inference.
    '''    
    def __init__(self, cfg):
        super().__init__()
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.cfg = cfg
        self.engine = None
        self.inputs = None
        self.outputs = None
        self.bindings = None
        self.stream = None
        self.context = None
        print(f'inside TensorRTLinear')

    def compile(self):
        print('Nothing to compile')

    def create_model(self):
        print("should not creaate TensorRTLinear model, it is created using post processing")

    def load(self, model_path):
        # uff_model = Path(model_path)
        # metadata_path = Path('%s/%s.metadata'
        #                      % (uff_model.parent.as_posix(), uff_model.stem))
        # with open(metadata_path.as_posix(), 'r') as metadata, \
        #         trt.Builder(self.logger) as builder, \
        #         builder.create_network() as network, \
        #         trt.UffParser() as parser:

        #     builder.max_workspace_size = 1 << 20
        #     builder.max_batch_size = 1
        #     builder.fp16_mode = True

        #     metadata = json.loads(metadata.read())
        #     # Configure inputs and outputs
        #     print('Configuring I/O')
        #     input_names = metadata['input_names']
        #     output_names = metadata['output_names']
        #     for name in input_names:
        #         parser.register_input(name, (self.cfg.TARGET_D,
        #                                      self.cfg.TARGET_H,
        #                                      self.cfg.TARGET_W))

        #     for name in output_names:
        #         parser.register_output(name)
        #     # Parse network
        #     print('Parsing TensorRT Network')
        #     parser.parse(uff_model.as_posix(), network)
        #     print('Building CUDA Engine')
        #     self.engine = builder.build_cuda_engine(network)
        # Allocate buffers
        print("load tensorrt engine")
        self.engine = eng.load_engine(eng.trt_runtime, model_path)
        
        print('Allocating Buffers')
        self.inputs, self.outputs, self.bindings, self.stream \
            = TensorRTLinear.allocate_buffers(self.engine)
        print("creating context")
        self.context = self.engine.create_execution_context()
        print('Ready')

    def inference(self, image, other_arr=None):
        # Channel first image format
        image = image.transpose((2,0,1)).ravel().astype(np.float32) * 1.0 / 255.0
        
        # image = image.astype(np.float32) * 1.0 / 255.0
        # Flatten it to a 1D array.
        # image = image.ravel()
        # The first input is the image. Copy to host memory.
        image_input = self.inputs[0] 
        np.copyto(image_input.host_memory, image)
        # with self.engine.create_execution_context() as context:
        inference_output = TensorRTLinear.infer(context=self.context,
                                                bindings=self.bindings,
                                                inputs=self.inputs,
                                                outputs=self.outputs,
                                                stream=self.stream)
        
        return inference_output
        

    def interpreter_to_output(self, interpreter_out):
        if len(interpreter_out) == 2:
            [throttle, steering] = interpreter_out
            # print(f"steering={steering} throttle={throttle}")
            # return -0.25, 0.3
            # return steering[0], throttle[0]
            return steering[0], 0.28
        else:
            [steering] = interpreter_out
            # print(f"steering={steering}")
            return steering[0], calculate_throttle(steering[0])

    @classmethod
    def allocate_buffers(cls, engine):
        inputs = []
        outputs = []
        bindings = []
        stream = cuda.Stream()
        for binding in engine:
            size = trt.volume(engine.get_binding_shape(binding)) \
                   * engine.max_batch_size
            dtype = trt.nptype(engine.get_binding_dtype(binding))
            # Allocate host and device buffers
            host_memory = cuda.pagelocked_empty(size, dtype)
            device_memory = cuda.mem_alloc(host_memory.nbytes)
            bindings.append(int(device_memory))
            if engine.binding_is_input(binding):
                inputs.append(HostDeviceMemory(host_memory, device_memory))
            else:
                outputs.append(HostDeviceMemory(host_memory, device_memory))

        return inputs, outputs, bindings, stream

    @classmethod
    def infer(cls, context, bindings, inputs, outputs, stream, batch_size=1):
        # Transfer input data to the GPU.
        [cuda.memcpy_htod_async(inp.device_memory, inp.host_memory, stream)
         for inp in inputs]
        # Run inference.
        context.execute_async(batch_size=batch_size, bindings=bindings,
                              stream_handle=stream.handle)
        # Transfer predictions back from the GPU.
        [cuda.memcpy_dtoh_async(out.host_memory, out.device_memory, stream)
         for out in outputs]
        # Synchronize the stream
        stream.synchronize()
        # Return only the host outputs.
        return [out.host_memory for out in outputs]
