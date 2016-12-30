

import os

import settings
import random
from utils import train as train_utils

all_img_paths = []

sessions_dir = settings.RECORDS_DIR 

sessions = ['port']

for s in sessions:
    session_path = os.path.join(sessions_dir, s)

    filtered_img_paths = train_utils.filter_session(session_path)
    all_img_paths += filtered_img_paths

print(len(all_img_paths))

random.shuffle(all_img_paths)

vgen = train_utils.variant_noflip_generator(all_img_paths)


p = settings.predictor()

p.create('port')
p.model.fit_generator(vgen, samples_per_epoch=1000, nb_epoch=10)

p.save()