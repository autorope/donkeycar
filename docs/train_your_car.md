# Train your car.
This doc will walk you through how to setup your donkey.


## Bill of Materials.
#### Required
1. Start your recording / predicting server on your laptop. 
   ``` 
   python manage.py drive --session pisesion --model basic --remote http://192.168.1.4:8886
   ```


### On Car
1. python serve 



## Make Video
ffmpeg -framerate 30/1 -pattern_type glob -i hood1/frame_*.jpg -c:v libx264 -r 30 -pix_fmt yuv420p -threads 2  -y output.mp4