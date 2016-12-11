## Donkey 
The the sidewalk self driving vehicle (auto). 


### Driving

Find your Raspberry Pi:
   sudo nmap -sP 192.168.1.0/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'