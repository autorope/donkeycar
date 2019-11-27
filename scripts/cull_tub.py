'''
Usage:
    cull_tub.py --tub=<path> --count=<int>

Note:
    This script will remove records in a given tub until it reaches a desired count.
    It will try to sample from the records to maintain a even steering distribution
    as it selects records to remove.
'''

import os

from docopt import docopt
import json

import donkeycar as dk
from donkeycar.utils import *
from donkeycar.parts.datastore import TubGroup

def main(tub_path, count):
    cfg = dk.load_config('config.py')
    records_paths = gather_records(cfg, tub_path)

    record_name = "user/angle"
    num_bins = 20
    half_bins = num_bins // 2
    bins = {}
    records = []

    for i in range(num_bins):
        bins[i] = []


    if len(records_paths) <= count:
        print("we have fewer records than target count.")
        return

    #put the record in a bin based on angle. expecting -1 to 1
    for record_path in records_paths:
        with open(record_path, 'r') as fp:
            record = json.load(fp)
        user_angle = float(record["user/angle"])
        record["filename"] = record_path
        iBin = round((user_angle * half_bins)  + (half_bins - 1)) % num_bins
        bins[iBin].append(record)
        records.append(record)


    for i in range(num_bins):
        print("iBin:", len(bins[i]))


    keep = []
    iBin = 0
    while len(keep) < count:
        iBin += 1
        if iBin >= num_bins:
            iBin = 0
        num_elem = len(bins[iBin]) 
        if num_elem > 0:
            iRec = random.randint(0, num_elem - 1)
            rec = bins[iBin].pop(iRec)
            keep.append(rec)

    print("have", count, "records selected. removing the rest...")

    
    for record in records:
        if record in keep:
            continue
        img_filename = os.path.join(tub_path, record['cam/image_array'])
        os.unlink(img_filename)
        os.unlink(record["filename"])

    print('done')
    
if __name__ == '__main__':
    args = docopt(__doc__)

    count = int(args["--count"])
    main(args["--tub"], count)
