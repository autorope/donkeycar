
# Stop Sign Detection

This part utilize a Google Coral accelerator and a pre-trained object detection model by Coral project to perform stop sign detection. If the donkey car see a stop sign, it will override the ```pilot/throttle``` to 0. In addition, a bounding box will be annotated to the ```cam/image_array```.

<video style="width:50%" controls>
  <source src="../../assets/parts/stop_sign_detection/demo.mp4" type="video/mp4">
Your browser does not support the video tag.
</video>

---------------

## Requirement
To use this part, you must have:

- [Google Coral USB Accelerator](https://coral.ai/products/accelerator/)

## How to use
Put the following lines in ```myconfig.py```
```
STOP_SIGN_DETECTOR = True
STOP_SIGN_MIN_SCORE = 0.2
STOP_SIGN_SHOW_BOUNDING_BOX = True
```

### Install Edge TPU dependencies

Follow [this instruction ](https://coral.ai/docs/accelerator/get-started) to install and setup Google Coral on Pi 4

In addition, install the dependency on your dev pc or pi4 like this

```
pip3 install https://dl.google.com/coral/edgetpu_api/edgetpu-2.14.0-py3-none-any.whl

```

## Detecting other objects

Since the pre-trained model are trained on coco, there are 80 objects that the model is able to detect. You can simply change the ```STOP_SIGN_CLASS_ID``` in ```stop_sign_detector.py``` to try.

## Accuracy

Since SSD [is not good at detecting small objects](https://medium.com/@jonathan_hui/what-do-we-learn-from-single-shot-object-detectors-ssd-yolo-fpn-focal-loss-3888677c5f4d), the accuracy of detecting the stop sign from far away may not be good. There are some ways that we can make enhancement but this is out of the scope of this part.


