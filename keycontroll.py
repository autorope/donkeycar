'''
Code to manually set the speed and angle of the vehicle. 
angle: the angle of the wheels ranging between -90 (full left)
        and 90 (full right)
speed: desired speed of the vehicle ranging between 100 (full forward)
        and -100 full backward

Key Commands:
i - speed up
k - slow down
j - turn left
l - turn right

'''



import threading
from time import sleep

from pynput.keyboard import Key, Listener, KeyCode

ANGLE_INTERVAL = 5
MAX_ANGLE = 90

SPEED_INTERVAL = 5
MAX_SPEED = 100


def on_press(key):
    global angle
    global speed
    global stop

    if key == KeyCode(char="i"): #speed up
        speed = min(speed + SPEED_INTERVAL, MAX_SPEED)
    
    elif key == KeyCode(char="k"): #slow down speed
        speed = max(speed - SPEED_INTERVAL, -MAX_SPEED)
    
    elif key == KeyCode(char="j"): #angle left
        angle = max(angle - ANGLE_INTERVAL, -MAX_ANGLE)
    
    elif key == KeyCode(char="l"): #angle right
        angle = min(angle + ANGLE_INTERVAL, MAX_ANGLE)

    elif key == Key.space: #togle stop
        print('stop pressed')
        stop = not stop

    elif key == Key.backspace:
        print('reseting angle and speed to zero')
        angle = 0
        speed = 0


# Collect events until released

def start_keyboard_listener():
    with Listener(
          on_press=on_press) as listener:
      listener.join()




if __name__ == '__main__':

    '''
    example how to use
    '''

    angle = 0
    speed = 0
    stop = True

    t = threading.Thread(target=start_keyboard_listener)
    t.daemon = True #to close thread on Ctrl-c
    t.start()

    while True:
        sleep(1)
        print('angle: %s,  speed: %s' %(angle, speed))