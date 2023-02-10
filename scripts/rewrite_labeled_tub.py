#!/usr/bin/env python3
"""
Scripts to propagate label to image's metadata

Usage:
    rewrite_labeled_tub.py [--label_key=<key used to store label> --in_tub=<input tub dir> --out_tub=<output tub dir> [--remove_unlabeled]]

Options:
    -h --help               Show this screen.
"""

import os
import shutil
import time
import logging
import json
from pathlib import Path
from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.types import TubRecord

from docopt import docopt
from tqdm import tqdm

import donkeycar as dk



class tubProcessor:

    def __init__(self,
                label_key:str, in_tub : str, out_tub: str, filter, cfg) -> None:

        inputs=['cam/image_array','user/angle', 'user/throttle', 'user/mode']
        types=['image_array','float', 'float','str']
        inputs += ['enc/speed']
        types += ['float']
        meta=[]
        self.label_key = label_key
        self.in_tub = in_tub
        self.out_tub = out_tub
        self.filter=filter
        self.tub = Tub(base_path=self.in_tub, inputs=inputs, types=types, metadata=meta)
        self.cfg = cfg

    def processRecords(self) -> None:
    
        shutil.rmtree(self.out_tub,ignore_errors=True)

        tub_full = Tub(base_path=self.out_tub,
                inputs=self.tub.manifest.inputs +
                [self.label_key],
                types=self.tub.manifest.types + ['str'])

        print (tub_full.manifest.inputs)
        print (tub_full.manifest.types)
        print (f"Filtering unlabeled images : {self.filter}")
        labels = list(self.tub.manifest.labeled_indexes.keys())
        print (labels)
        for idx, record in enumerate(tqdm(self.tub)):
            t = TubRecord(self.cfg, self.tub.base_path, record)
            img = t.image()

            newRecord = t.underlying
            newRecord['cam/image_array'] = img
            newRecord[self.label_key]="" 
            for aLabel in labels:
                if idx in self.tub.manifest.labeled_indexes[aLabel] :
                    newRecord[self.label_key] = aLabel
            if self.filter == False or len(newRecord[self.label_key]) > 0:
                tub_full.write_record(newRecord)

        print (f"Proccessed Tub {self.in_tub} saved to {self.out_tub}")


if __name__ == '__main__':
    args = docopt(__doc__)
    cfg = dk.load_config()

    label_key = args['--label_key']
    in_tub = args['--in_tub']
    out_tub = args['--out_tub']
    filter = args['--remove_unlabeled']
    tub_path = cfg.DATA_PATH
    processor = tubProcessor(label_key, in_tub, out_tub, filter, cfg)
    processor.processRecords()