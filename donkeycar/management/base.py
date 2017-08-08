#!/usr/bin/env python3
"""
Upload a file to S3 (requires amazon credentials).

Usage:
     donkey <command> [--file_path=<file_path>]

Options:
  --file_path=<file_path> name of dataset file to save.
  --bucket=<bucket>  name of S3 bucket to upload data. [default: donkey_resources].
"""

from docopt import docopt
import sys
import os
import socket
import shutil
import argparse

PACKAGE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_PATH = os.path.join(PACKAGE_PATH, 'templates')

def make_dir(path):
    real_path = os.path.expanduser(path)
    print('making dir ', real_path)
    if not os.path.exists(real_path):
        os.makedirs(real_path)
    return real_path


class BaseCommand():
    pass


class CreateCar(BaseCommand):
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='createcar', usage='%(prog)s [options]')
        parser.add_argument('--path', help='path where to create car folder')
        parser.add_argument('--template', help='name of car template to use')
        
        parsed_args = parser.parse_args(args)
        return parsed_args
        
    def run(self, args):
        args = self.parse_args(args)
        print(args.path)
        self.create_car(path=args.path, template=args.template)
    
    def create_car(self, path, template):
        """
        This script sets up the folder struction for donkey to work. 
        It must run without donkey installed so that people installing with
        docker can build the folder structure for docker to mount to.
        """
        
        path = path or '~/mydonkey'
        template = template or 'donkey2'
        
        
        path = make_dir(path)
        
        print("Creating folders to hold training data and pilot models.")
        folders = ['models', 'data', 'logs']
        folder_paths = [os.path.join(path, f) for f in folders]   
        for fp in folder_paths:
            make_dir(fp)
            
        print("Copying car template.")
        template_path = os.path.join(TEMPLATES_PATH, template+'.py')
        new_path = os.path.join(path, 'car.py')
        shutil.copyfile(template_path, new_path)
        print(new_path)

        print("Donkey setup complete.")



class UploadData(BaseCommand):
    
    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='uploaddata', usage='%(prog)s [options]')
        parser.add_argument('--url', help='path where to create car folder')
        parser.add_argument('--template', help='name of car template to use')
        
        parsed_args = parser.parse_args(args)
        return parsed_args



class FindCar(BaseCommand):
    def parse_args(self, args):
        pass        

        
    def run(self, args):
        print('Looking up your computer IP address...')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8",80))
        ip = s.getsockname()[0] 
        print('Your IP address: %s ' %s.getsockname()[0])
        s.close()
        
        print("Finding your car's IP address...")
        cmd = "sudo nmap -sP " + ip + "/24 | awk '/^Nmap/{ip=$NF}/B8:27:EB/{print ip}'"
        print("Your car's ip address is:" )
        os.system(cmd)
        


def execute_from_command_line():
    
    commands = {
            'createcar': CreateCar,
            'findcar': FindCar
            #'calibratesteering': CalibrateSteering,
                }
    
    args = sys.argv[:]
    command_text = args[1]
    
    if command_text in commands.keys():
        command = commands[command_text]
        c = command()
        c.run(args[2:])
    else:
        print('The availible commands are:')
        print(list(commands.keys()))
        
    
    