## Donkey 
The the sidewalk self driving vehicle (auto). 


### Driving

Find your Raspberry Pi:
   sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'


TODO: 
Try setting global variables (angle & speed) from a Tornado Webpage. 
	If this doesn't work. Write them to an sqldatabase and read them from the drive loop. 
Control vehicle from the tornado site running on raspbery pi. 

Stream the video from the camera.
http://www.chioka.in/python-live-video-streaming-example/