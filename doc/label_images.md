# How to label images with donkey ui and a side script

## Principle 
To avoid breaking `donkey ui` a lot, idea is the following :
- in `donkey ui` we can assign each images to one of the possible label class defined in ui.kv :
```
#:set labels ['NA','left', 'right', 'middle']
``` 
- The way label information is stored is similar to the way images are deleted from a tub. A new array named `labeled_indexes` in manifest file is used to store images index belonging to one of the label (dict of array)
- a script (`script/rewrite_labeled_tub.py`) is used to re-create a tub, using `labeled_indexes` from manifest to rebuild image attributes accordingly. 

Steps are then the following:
- review and label images with `donkey ui`
- reprocess tub and create new tub with `script/rewrite_labeled_tub.py`

## Donkey UI
- Using Tub Manager, make sure you have the right `car directory` and `tub directory` selected
- Label image or group of images as follow :
    - use regular Tub control buttons to jump to the first image you want to label
    - select the label you want from the `Label` drop down (next to `Apply Label` button)
    - use regular tub control button to jump to the last image 
    - click on `Apply Label` button (warning, last image is always exluded from the selected group when applying label, as well as when deleting images)
- current label of an images if shown above Tub control buttons, next to Record index

## Script
- To have data prepared for training, we need to to have label availabled as image metadata, similarly as angle and thorttle.
- For that prupose, script `script/rewrite_labeled_tub.py` is provided.

Usage :
```
rewrite_labeled_tub.py [--label_key=<key used to store label> --in_tub=<input tub dir> --out_tub=<output tub dir> [--remove_unlabeled]]
```

As an example, if your tub data is in directory `data` of your car directory (the regular case), and if you want to have label recorded in a metadata with key `label/car_ahead`, then you can invoke script as below :
```
~/donkeycar/scripts/rewrite_labeled_tub.py --label_key="label/car" --in_tub=data --out_tub=data_labeled
```
A new tub in directory `data_labeled` is the created. You can inscpect it with `donkey ui`