#Cull many tubs
import os
import sys

from cull_tub import main

tubs = os.listdir(sys.argv[1])
count = int(sys.argv[2])
print("found", len(tubs), "tubs")
for tub in tubs:
    if os.path.isdir(tub):
        print("working on", tub)
        main(tub, count)