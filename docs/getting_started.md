## Drive your car.

Now that you have built your car, you'll want to drive it. 

#### Start your server 
1. Open a termial and find your ip address by typing `ifconfig`
2. Start a server by running the `serve_no_pilot.py` demo script.
3. Now you can load the control page at `localhost:8887`

#### Start your car

1. Open another terminal
2. Use this code to find the ip address of your pi. Change the IP base ip address to match your router.

   	```
    sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'
    ```
3. Connect to your pi by running `ssh pi@<your_pi_ip_address>`
4. Activate your python virtual environment 
	```
	cd donkey
	source env/bin/activate
	```
5. Start your drive script.
	```
	python scripts/drive.py  --remote http://<your server address>:8887
	``` `


#### Control your car
You can now control your car with the virtual joystic on your computer or your phone.
