import click
import os
import donkeycar as dk
import logging
import tarfile
import numpy as np
from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.types import TubRecord
from donkeycar.config import load_config


@click.command()
@click.option('--mycar', '-c')
@click.option('--tub', '-t')
def main(mycar, tub):
    MirrorTub(mycar, tub)


class MirrorTub(object):

    def __init__(self, mycar, tub):
        self.cfg = load_config(os.path.join(mycar, 'config.py'))

        if ' ' in tub:
            for tub in tub.split():
                self.mirrorTub(mycar, tub)
        else:
            self.mirrorTub(mycar, tub)

    def mirrorTub(self, my_car_path, tub):

        # put your path to donkey project
        tar = tarfile.open(os.path.expanduser(
            '/Users/karli/donkey/donkeycar/donkeycar/tests/tub/tub.tar.gz'))
        tub_parent = os.path.join(my_car_path, 'data/')
        new_tub_parent = os.path.join(my_car_path, 'data_flipped/')
        tar.extractall(tub_parent)

        tub_path = os.path.join(tub_parent, tub)
        tub1 = Tub(tub_path)
        tub2 = Tub(os.path.join(new_tub_parent, tub),
                   inputs=['cam/image_array', 'user/angle', 'user/throttle',
                           "behavior/label", "behavior/one_hot_state_array", "behavior/state"],
                   types=['image_array', 'float', 'float', 'str', 'vector', 'int'])

        new_records = {}
        for key, record in enumerate(tub1):
            new_records[key] = record

        def flipCcmd(state):
            if state == 0:
                return {"label": "Right", "state": 2, "one_hot_state_array": [0.0, 0.0, 1.0]}
            elif state == 2:
                return {"label": "Left", "state": 0, "one_hot_state_array": [1.0, 0.0, 0.0]}
            else:
                return {"label": "Straight", "state": 1, "one_hot_state_array": [0.0, 1.0, 0.0]}

        turn_count = 0
        last_angle = 0
        for key, record in enumerate(tub1):

            t_record = TubRecord(config=self.cfg,
                                 base_path=tub1.base_path,
                                 underlying=record)
            img_arr = t_record.image(cached=False)

            record['cam/image_array'] = np.flip(img_arr, axis=1)

            tub2.write_record(record)


if __name__ == "__main__":
    main()
