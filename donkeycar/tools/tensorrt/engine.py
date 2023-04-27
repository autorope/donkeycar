import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
trt_runtime = trt.Runtime(TRT_LOGGER)
ctx = pycuda.autoinit.context
trt.init_libnvinfer_plugins(None, "")

def build_engine(onnx_path, shape = [1,224,224,3]):

   """
   This is the function to create the TensorRT engine
   Args:
      onnx_path : Path to onnx_file. 
      shape : Shape of the input of the ONNX file. 
  """
   print(f"building trt engine with shape {shape}")
    
   with trt.Builder(TRT_LOGGER) as builder, builder.create_network(1) as network, builder.create_builder_config() as config, trt.OnnxParser(network, TRT_LOGGER) as parser:
       
       config.max_workspace_size = (256 << 20) # 256MB
       # config.max_workspace_size = 1 << 30   # 1GB
       # config.set_flag(trt.BuilderFlag.FP16)

       with open(onnx_path, 'rb') as model:
           parser.parse(model.read())
       
       network.get_input(0).shape = shape
       
       builder.max_batch_size = 1
       engine = builder.build_engine(network, config)
       
       return engine

def save_engine(engine, file_name):
   buf = engine.serialize()
   with open(file_name, 'wb') as f:
       f.write(buf)
def load_engine(trt_runtime, plan_path):
   with open(plan_path, 'rb') as f:
       engine_data = f.read()
   engine = trt_runtime.deserialize_cuda_engine(engine_data)
   return engine


