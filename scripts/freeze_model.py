'''
Usage:
    freeze_model.py --model="mymodel.h5" --output="frozen_model.pb"

Note:
    This requires that TensorRT is setup correctly. For more instructions, take a look at
    https://docs.nvidia.com/deeplearning/sdk/tensorrt-install-guide/index.html
'''
import os

from docopt import docopt
import tensorflow as tf

args = docopt(__doc__)
in_model = os.path.expanduser(args['--model'])
output = os.path.expanduser(args['--output'])

# Reset session
tf.keras.backend.clear_session()
tf.keras.backend.set_learning_phase(0)

model = tf.keras.models.load_model(in_model, compile=False)
session = tf.keras.backend.get_session()

input_names = [layer.op.name for layer in model.inputs]
output_names = [layer.op.name for layer in model.outputs]
graph = session.graph

# Freeze Graph
with graph.as_default():
    # Remote training nodes
    graph_frozen = tf.compat.v1.graph_util.remove_training_nodes(graph.as_graph_def())
    # Convert variables to constants
    graph_frozen = tf.compat.v1.graph_util.convert_variables_to_constants(session, graph_frozen, output_names)
    with open(output, 'wb') as output_file:
        output_file.write(graph_frozen.SerializeToString())

    print ('Inputs = [%s], Outputs = [%s]' % (input_names, output_names))
    print ('To convert use: \n   `convert-to-uff %s`' % (output))

