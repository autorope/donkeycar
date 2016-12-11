
import tty, sys #used for live keyboard input
import argparse
from time import sleep
import curses

#from picamera import PiCamera

from whip import Whip

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='sub-command help', dest="subparser_name")

parser_a = subparsers.add_parser('drive', help='drive help')
parser_b = subparsers.add_parser('record', help='record help')

args = parser.parse_args()


BASE_URL = 'http://localhost:8000/'
PHOTOS_PATH = '/home/wroscoe/.tmp/'



def drive():
    whip = Whip(BASE_URL)


def record(stdscr):
    ''' record pictures on an interval '''
    #camera = PiCamera()

    file_num = 0

    # do not wait for input when calling getch
    stdscr.nodelay(1)
    while True:
        # get keyboard input, returns -1 if none available
        c = stdscr.getch()
        if c != -1:
            # print numeric value
            stdscr.addstr(str(c) + ' ')
            stdscr.refresh()
            # return curser to start position
            stdscr.move(0, 0)

        sleep(1)
        print('capturing')
        #camera.capture()

        file_name = 'donkey_' + str(file_num)
        file_num += 1







if __name__ == '__main__':
    if 'subparser_name' in args:
        if args.subparser_name == 'drive':
            print('starting donkey in drive mode') 
            print('press "d" to exit') 
            curses.wrapper(drive)
        elif args.subparser_name == 'record':
            print('starting donkey in drive mode') 
            print('press " " to exit') 
            curses.wrapper(record)
