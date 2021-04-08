import os
import shutil
import timeit
from pathlib import Path

import numpy as np

from donkeycar.parts.tub_v2 import Tub


def benchmark():
    # Change to a non SSD storage path
    path = Path('/media/rahulrav/Cruzer/benchmark')

    # Recreate paths
    if os.path.exists(path.absolute().as_posix()):
        shutil.rmtree(path)

    inputs = ['input']
    types = ['int']
    tub = Tub(path.as_posix(), inputs, types, max_catalog_len=1000)
    write_count = 1000
    for i in range(write_count):
        record = {'input': i}
        tub.write_record(record)

    deletions = np.random.randint(0, write_count, 100)
    tub.delete_records(deletions)
 
    for record in tub:
        print('Record %s' % record)

    tub.close()


if __name__ == "__main__":
    timer = timeit.Timer(benchmark)
    time_taken = timer.timeit(number=1)
    print('Time taken %s seconds' % time_taken)
    print('\nDone.')
