"""
For large sessions that won't fit in memory you'll need to use a generator.

This example shows how to use a generator and only save the model that has 
the lowest validation loss. 
"""

import donkey as dk
from keras.callbacks import ModelCheckpoint

#Read in pictures and velocities and create a predictor
sh = dk.sessions.SessionHandler(sessions_path='~/donkey_data/sessions/')
s = sh.load('test')


#split training and test data. 
all_imgs = s.img_paths()
train_imgs, test_imgs = dk.utils.split_list(all_imgs, test_frac=.8, sequential=True)

train_gen = s.load_generator(add_dim=True, img_paths=train_imgs)
test_gen = s.load_generator(add_dim=True, img_paths=test_imgs)


# Use a checkpoint to save best model after each epoch
filepath="best_model.hdf5"
checkpoint = ModelCheckpoint(filepath, monitor='val_loss', verbose=1, 
                             save_best_only=True, mode='min')
callbacks_list = [checkpoint]

#use 3 layer convolution netowrk with one fully connected
model = dk.models.cnn3_full1()

#fit model with generator
model.fit_generator(train_gen, samples_per_epoch=70, nb_epoch=8, 
                    validation_data=test_gen, nb_val_samples=100, callbacks=callbacks_list)