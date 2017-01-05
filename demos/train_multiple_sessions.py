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
#x, y = s1.load_data()
#model.fit(x,y)

all_imgs = s1.img_paths()
train_imgs, test_imgs = dk.utils.split_list(all_imgs, test_frac=.8, sequential=True)


train_gen = s1.load_generator(add_dim=True, img_paths=train_imgs)
test_gen = s1.load_generator(add_dim=True, img_paths=test_imgs)


# Checkpoint the weights when validation accuracy improves
from keras.models import Sequential
from keras.layers import Dense
from keras.callbacks import ModelCheckpoint
import matplotlib.pyplot as plt

# checkpoint
#filepath="weights-improvement-{epoch:02d}-{val_loss:.2f}.hdf5"
filepath="best_model.hdf5"
checkpoint = ModelCheckpoint(filepath, monitor='val_loss', verbose=1, save_best_only=True, mode='min')
callbacks_list = [checkpoint]
# Fit the model


model.fit_generator(train_gen, samples_per_epoch=70, nb_epoch=8, validation_data=test_gen, nb_val_samples=100, callbacks=callbacks_list)