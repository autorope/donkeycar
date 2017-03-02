"""
Convienience script to find your Raspberry Pi on a local network. 

Usage:
    find_car.py [--ip=<ip>]

Options:
  --ip=<ip>   Base ip address of your network [default: 192.168.1.0]
"""


from docopt import docopt
import os
import socket

args = docopt(__doc__)
ip = args['--ip']

print('Looking up your computer IP address...')
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8",80))
print('Your IP address: %s ' %s.getsockname()[0])
s.close()


import subprocess

print("Finding your car's IP address...")
cmd = "sudo nmap -sP " + ip + "/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'"
print("Your car's ip address is:" )
os.system(cmd)



