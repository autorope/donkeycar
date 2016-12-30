
 """Records training data and / or drives the car with tensorflow.
Usage:
    train.py [--session=<name>] [--model=<name>]

Options:
  --model=<name>     model name for predictor to use 
  --session=<name>   recording session name
"""

import settings

from docopt import docopt

# Get args.
args = docopt(__doc__)
session = args['--session'] or None
model = args['--model'] or None

if __name__ == '__main__':


    #Read in pictures and velocities and create a predictor
    recorder = settings.recorder(session)
    
    predictor = settings.predictor()
    predictor.create(model)

    print('getting arrays')
    x, y = recorder.get_arrays()
    print('fitting model')
    predictor.fit(x, y)
    predictor.save()