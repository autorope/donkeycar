#!/usr/bin/env python3
# Author: Roma Sokolkov (r7vme) 2018

'''
  Script to augment tub data by flopping images and steering angle.
  It will output new tub into separate directory with "_flopped"
  suffix.

  Usage: ./flop_tub.py <tub directory>
'''

import os
import json
import sys

from shutil import copyfile

if __name__ == "__main__":
    # Exit if no target directory.
    if len(sys.argv) == 1 :
        print("usage: {0} <tub directory to flop>".format(sys.argv[0]))
        sys.exit(1)

    try:
        from PIL import Image
    except ModuleNotFoundError:
        print("error: Pillow not found. To install use \"pip install Pillow\".")
        sys.exit(1)

    tub_path_orig = os.path.normpath(sys.argv[1])
    tub_path_conv = tub_path_orig + "_flopped"

    if not os.path.exists(tub_path_orig):
        print("error: {0} does not exist".format(tub_path_orig))
        sys.exit(1)

    if not os.path.exists(tub_path_conv):
        os.makedirs(tub_path_conv)

    files = os.listdir(tub_path_orig)
    total = len(files)
    processed = 0
    for f in files:
        fpath = os.path.join(tub_path_orig, f)
        fpath_conv = os.path.join(tub_path_conv, f)

        # Flop every jpg file in directory and output to the new tub directory.
        if fpath.endswith("jpg"):
            with Image.open(fpath) as im:
                im.transpose(Image.FLIP_LEFT_RIGHT).save(fpath_conv)

        # Flop angle in every record file and output to the new tub directory.
        if os.path.basename(fpath).startswith("record_"):
            data = json.load(open(fpath))
            data["user/angle"] = -data["user/angle"]
            with open(fpath_conv, "w") as outfile:
                json.dump(data, outfile)

        if os.path.basename(fpath) == "meta.json":
            copyfile(fpath, fpath_conv)

        # Show progress to the user.
        processed += 1
        os.listdir(tub_path_orig)
        sys.stdout.write('Processed {0}/{1} files\r'.format(processed, total))
        sys.stdout.flush()
