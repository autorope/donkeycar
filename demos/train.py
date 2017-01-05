"""
Example of how to train a pilot from the images
of saved in a prior drive session. 
"""

import donkey as dk


#Read in pictures and velocities and create a predictor
sh = dk.sessions.SessionHandler(sessions_path='~/donkey_data/sessions/')
s1 = sh.load('port')


model = dk.models.cnn3_full1()
model.compile(loss='mse', optimizer='adam')


print('getting arrays')
x, y = s1.load_data()
model.fit(x,y)


'''
Proposed way to build pilot
model.load('/path_to_trained_model')
class BasePilot():
    def __init__(self, model):
        self.model = model

    def decide(img_arr, data)

'''

