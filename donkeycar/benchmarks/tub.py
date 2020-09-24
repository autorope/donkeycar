import json
import os
import shutil
import timeit
from pathlib import Path

import numpy as np

from donkeycar.parts.datastore import Tub


def benchmark():
    # Change with a non SSD storage path
    path = Path('/media/rahulrav/Cruzer/tub')
    if os.path.exists(path.absolute().as_posix()):
        shutil.rmtree(path)

    inputs = ['input']
    types = ['int']
    tub = Tub(path.absolute().as_posix(), inputs, types)
    write_count = 1000
    for i in range(write_count):
        record = {'input': i}
        tub.put_record(record)

    # old tub starts counting at 1
    deletions = set(np.random.randint(1, write_count + 1, 100))
    for index in deletions:
        index = int(index)
        tub.remove_record(index)

    files = path.glob('*.json')
    for record_file in files:
        contents = record_file.read_text()
        if contents:
            contents = json.loads(contents)
            print('Record %s' % contents)


if __name__ == "__main__":
    timer = timeit.Timer(benchmark)
    time_taken = timer.timeit(number=1)
    print('Time taken %s seconds' % time_taken)
    print('\nDone.')
