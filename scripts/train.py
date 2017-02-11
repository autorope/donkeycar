"""
Example of how to train a keras model from simulated images or a 
previously recorded session.

"""

import donkey as dk

#Train on session pictures
#sh = dk.sessions.SessionHandler(sessions_path='~/donkey_data/sessions/')
#s = sh.load('manual_white_line')
#X, Y = s.load_dataset()


#Train on simulated pictures
X, Y = dk.datasets.moving_square(n_frames=2000, return_x=True, return_y=False)


#print('Downloading file, this could take some time.')
#url = 'https://s3.amazonaws.com/donkey_resources/port.pkl'
#X, Y = dk.datasets.load_url(url)

print('Loading Model.')
model = dk.models.cnn3_full1()



model.fit(X,Y, nb_epoch=10, validation_split=0.2)


model.save('test_model')