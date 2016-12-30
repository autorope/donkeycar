"""
Example of how to train a pilot from the images
of saved in a prior drive session. 
"""

from donkey.pilots import keras
from donkey.recorders import FileRecorder

#Read in pictures and velocities and create a predictor
recorder = FileRecorder(session='port',
                        sessions_dir='~/donkey_data/sessions/')

pilot = keras.CNN()

print('getting arrays')
x, y = recorder.get_arrays()

print('fitting model')
pilot.train(x, y)

pilot.save('mycnn')