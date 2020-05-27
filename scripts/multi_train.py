'''
multi_train.py

This script can be dropped into your car dir next to manage.py.
This will invoke a number of sub processes to drive some ai clients
and have them log into and drive on the SDSandbox donkey sim server.
Check: https://docs.donkeycar.com/guide/simulator/
'''
import os
import time
import random
import subprocess

num_clients = 4
model_file = "lane_keeper.h5" #or any model in ~/mycar/models/
body_styles = ["donkey", "bare", "car01"]
host = '127.0.0.1'
procs = []

for i in range(num_clients):
    conf_file = "client%d.py" % i
    with open(conf_file, "wt") as outfile:
        outfile.write('WEB_CONTROL_PORT = 888%d\n' % i)
        outfile.write('WEB_INIT_MODE = "local"\n')
        outfile.write('DONKEY_GYM = True\n')
        outfile.write('DONKEY_SIM_PATH = "remote"\n')
        outfile.write('SIM_HOST = "%s"\n' % host)
        iStyle = random.randint(0, len(body_styles) - 1)
        body_style = body_styles[iStyle]
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        outfile.write('GYM_CONF = { "body_style" : "%s", "body_rgb" : (%d, %d, %d), "car_name" : "ai%d", "font_size" : 100}\n' % (body_style, r, g, b, i+1))
        outfile.close()

    command = "python manage.py drive --model=models/%s --myconfig=%s" % (model_file, conf_file)
    com_list = command.split(" ")
    print(com_list)
    proc = subprocess.Popen(com_list)
    procs.append(proc)
    time.sleep(1)


print("running for 5 min...")
try:
    time.sleep(60 * 5)
except:
    pass

print("stopping ai")
for proc in procs:
    proc.kill()
print('done')
