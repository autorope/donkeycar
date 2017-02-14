# Datasets

Donkey has several builtin datasets to help users test their autopilots and confirm that they can learn from image sequences. 

## Moving Square
A single color moving square bounces around the screen.

Outputs:
* X - 120x160px image of moving square on black background.
* Y - x and y cordinates of center of square in the image. (use options to only return x or y)



## Driving Datasets
[Blog post showing how to train a model from these datasets](https://wroscoe.github.io/keras-lane-following-autopilot.html#keras-lane-following-autopilot)
DIYRobocars 1/10th scale track on Feb 11th - [warehouseRGB.pkl](https://s3.amazonaws.com/donkey_resources/warehouseRGB.pkl)
