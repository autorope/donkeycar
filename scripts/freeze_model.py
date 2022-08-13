'''
Usage:
    freeze_model.py --model="mymodel.h5" --output="frozen_model.pb"

Note:
    This requires that TensorRT is setup correctly. For more instructions, take a look at
    https://docs.nvidia.com/deeplearning/sdk/tensorrt-install-guide/index.html
'''
import os

from docopt import docopt
import json
from pathlib import Path
import tensorflow as tf

args = docopt(__doc__)
in_model = os.path.expanduser(args['--model'])
output = os.path.expanduser(args['--output'])
output_path = Path(output)
output_meta = Path('%s/%s.metadata' % (output_path.parent.as_posix(), output_path.stem))

tf.compat.v1.disable_eager_execution()

# Reset session
tf.keras.backend.clear_session()
tf.keras.backend.set_learning_phase(0)

model = tf.compat.v1.keras.models.load_model(in_model, compile=False)
session = tf.compat.v1.keras.backend.get_session()

input_names = sorted([layer.op.name for layer in model.inputs])
output_names = sorted([layer.op.name for layer in model.outputs])

# Store additional information in metadata, useful for infrencing
meta = {'input_names': input_names, 'output_names': output_names}

graph = session.graph

# Freeze Graph
with graph.as_default():
    # Convert variables to constants
    graph_frozen = tf.compat.v1.graph_util.convert_variables_to_constants(session, graph.as_graph_def(), output_names)
    # Remote training nodes
    graph_frozen = tf.compat.v1.graph_util.remove_training_nodes(graph_frozen)
    with open(output, 'wb') as output_file, open(output_meta.as_posix(), 'w') as meta_file:
        output_file.write(graph_frozen.SerializeToString())
        meta_file.write(json.dumps(meta))

    print ('Inputs = [%s], Outputs = [%s]' % (input_names, output_names))
    print ('Writing metadata to %s' % output_meta.as_posix())
    print ('To convert use: \n   `convert-to-uff %s`' % (output))

