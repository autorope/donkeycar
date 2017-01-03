## Drive your car.

Now that you have built your car, you'll want to drive it. 

#### Start your server 
1. Open a termial and find your ip address by typing `ifconfig`
2. Start a server by running the serve.py demo script.
3. Now you can load the control page at `localhost:8887`

#### Start your car

1. Open another terminal
2. Use this code to find the ip address of your pi. Change the IP base ip address to match your router.

   	```
    sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'
    ```
3. Connect to your pi by running `ssh pi@<your_pi_ip_address>`
4. Run the `drive.py` demo script
