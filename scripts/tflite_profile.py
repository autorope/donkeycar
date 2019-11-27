'''
Usage: 
    tflite_test.py --model="mymodel.tflite"

Note:
    may require tensorflow > 1.11 or
    pip install tf-nightly
'''
import os

from docopt import docopt
import tensorflow as tf
import numpy as np

from donkeycar.utils import FPSTimer

args = docopt(__doc__)

in_model = os.path.expanduser(args['--model'])

# Load TFLite model and allocate tensors.
interpreter = tf.lite.Interpreter(model_path=in_model)
interpreter.allocate_tensors()

# Get input and output tensors.
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Test model on random input data.
input_shape = input_details[0]['shape']
input_data = np.array(np.random.random_sample(input_shape), dtype=np.float32)

interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()

#sample output
for tensor in output_details:
    output_data = interpreter.get_tensor(tensor['index'])
    print(output_data)

#run in a loop to test performance.
print("test performance: hit CTRL+C to break")
timer = FPSTimer()
while True:
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    timer.on_frame()

