# A Guide to using TensorRT on the Nvidia Jetson Nano

----

* **Note** This guide assumes that you are using Ubuntu `18.04`. If you are using Windows refer to [these](https://docs.nvidia.com/deeplearning/sdk/tensorrt-install-guide/index.html) instructions on how to setup your computer to use TensorRT.

----

## Step 1: Setup TensorRT on Ubuntu Machine

Follow the instructions [here](https://docs.nvidia.com/deeplearning/sdk/tensorrt-install-guide/index.html#installing-tar). Make sure you use the `tar` file instructions unless you have previously installed CUDA using `.deb` files.

## Step 2: Setup TensorRT on your Jetson Nano

* Setup some environment variables so `nvcc` is on `$PATH`. Add the following lines to your `~/.bashrc` file.

```bash
# Add this to your .bashrc file
export CUDA_HOME=/usr/local/cuda
# Adds the CUDA compiler to the PATH
export PATH=$CUDA_HOME/bin:$PATH
# Adds the libraries
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

* Test the changes to your `.bashrc`.

```bash
source ~/.bashrc
nvcc --version
```

You should see something like:

```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2018 NVIDIA Corporation
Built on ...
Cuda compilation tools, release 10.0, Vxxxxx
```

* Switch to your `virtualenv` and install PyCUDA.

```bash
# This takes a a while.`
pip install pycuda
```

* After this you will also need to setup `PYTHONPATH` such that your `dist-packages` are included as part of your `virtualenv`. Add this to your `.bashrc`. This needs to be done because the python bindings to `tensorrt` are available in `dist-packages` and this folder is usually not visible to your virtualenv. To make them visible we add it to `PYTHONPATH`.

```bash
export PYTHONPATH=/usr/lib/python3.6/dist-packages:$PYTHONPATH
```

* Test this change by switching to your `virtualenv` and importing `tensorrt`.

```python
> import tensorrt as trt
> # This import should succeed
```

## Step 3: Train, Freeze and Export your model to TensorRT format (`uff`)

After you train the `linear` model you end up with a file with a `.h5` extension.

```bash
# You end up with a Linear.h5 in the models folder
python manage.py train --model=./models/Linear.h5 --tub=./data/tub_1_19-06-29,...
# Freeze model using freeze_model.py in donkeycar/scripts
# The frozen model is stored as protocol buffers.
# This command also exports some metadata about the model which is saved in ./models/Linear.metadata
python freeze_model.py --model=./models/Linear.h5 --output=./models/Linear.pb
# Convert the frozen model to UFF. The command below creates a file ./models/Linear.uff
convert-to-uff ./models/Linear.pb
```

Now copy the converted `uff` model and the `metadata` to your Jetson Nano.

## Step 4

* In `myconfig.py` pick the model type as `tensorrt_linear`.

```python
DEFAULT_MODEL_TYPE = `tensorrt_linear`
```

* Finally you can do

```bash
# After you scp your `uff` model to the Nano
python manage.py drive --model=./models/Linear.uff
```