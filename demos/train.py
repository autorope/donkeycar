"""
Example of how to train a pilot from the images
of saved in a prior drive session. 
"""

from donkey.pilots import keras
from donkey.datasets

#Read in pictures and velocities and create a predictor
sh = SessionHandler(sessions_path='~/donkey_data/sessions/')
s = sh.load('port')

print('getting arrays')
x, y = s.get_arrays()


pilot = keras.CNN()

print('fitting model')
pilot.train(x, y)

pilot.save('mycnn')