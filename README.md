## Donkey 
The the sidewalk self driving vehicle (auto). 


### Driving

Find your Raspberry Pi:
   sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'


TODO: 

Try running tornado in it's own thread. Or some other way to start the server from the main script 
and stop it when Ctrl-C is pressed. 

Try setting global variables (angle & speed) from a Tornado Webpage. 
	If this doesn't work. Write them to an sqldatabase and read them from the drive loop. 

Stream the video from the camera.
http://www.chioka.in/python-live-video-streaming-example/

Work on recording, uploading, driving commands 


Try controling vehicle from the tornado site running on raspbery pi. 

Train Network on new data. 


Try loading tensorflow on Pi to run Trained Network. 

Email Adam, Keven and Jeff about the Jan 22nd Race 


