import os
import sys
import glob
import json
import shutil

def go(src_path, dest_path):
    print('adding tub', src_path, 'to', dest_path)
    src_files = glob.glob(os.path.join(src_path, '*.jpg'))
    dest_files = glob.glob(os.path.join(dest_path, '*.jpg'))
    print('%d files in src, %d in dest.' %(len(src_files), len(dest_files)))
    dest_files.sort(key=lambda x: os.stat(x).st_mtime)
    src_files.sort(key=lambda x: os.stat(x).st_mtime)
    last = dest_files[-1]
    basename = os.path.basename(last)
    sl = basename.split('_')
    print('last num in dest:', sl[0], basename)
    num = int(sl[0])
    if num + 1 < len(src_files):
        print('warning>> last num found (%d) fewer than file count (%d).' %(num, len(dest_files)))
        return

    for src in src_files:
        basename = os.path.basename(src)
        sl = basename.split('_')
        snum = int(sl[0])
        #we add one because src is zero based
        dnum = snum + num + 1
        dest = basename.replace(str(snum), str(dnum))
        dest = os.path.join(dest_path, dest)
        #print('cp', src, dest)
        #copy jpg image
        shutil.copyfile(src, dest)

        src_json = os.path.join(src_path, "record_%d.json" % snum)
        dest_json = os.path.join(dest_path, "record_%d.json" % dnum)
        #print('cp', src_json, dest_json)
        #copy json record
        shutil.copyfile(src_json, dest_json)

        #read contents of json and modify to match new numbering
        with open(dest_json, 'r') as fp:
            json_data = json.load(fp)
        cam = json_data['cam/image_array']
        json_data['cam/image_array'] = cam.replace(str(snum), str(dnum))
        with open(dest_json, 'w') as fp:
            json.dump(json_data, fp)
            
        




if __name__ == '__main__':
    go(sys.argv[1], sys.argv[2])
