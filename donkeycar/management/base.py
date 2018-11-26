
import sys
import os
import socket
import argparse
from distutils.dir_util import copy_tree
import donkeycar as dk


PACKAGE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_PATH = os.path.join(PACKAGE_PATH, 'templates')


def make_dir(path):
    real_path = os.path.expanduser(path)
    print('making dir ', real_path)
    if not os.path.exists(real_path):
        os.makedirs(real_path)
    return real_path


def load_config(config_path):

    """
    load a config from the given path
    """
    conf = os.path.expanduser(config_path)

    if not os.path.exists(conf):
        print("No config file at location: %s. Add --config to specify\
                location or run from dir containing config.py." % conf)
        return None

    try:
        cfg = dk.load_config(conf)
    except:
        print("Exception while loading config from", conf)
        return None

    return cfg


class BaseCommand:
    pass


class CreateCar(BaseCommand):

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='createcar', usage='%(prog)s [options]')
        parser.add_argument('path')
        parser.add_argument('--template', default=None, help='name or path of car template to use')
        parser.add_argument('--overwrite', action='store_true', help='should replace existing files')

        parsed_args = parser.parse_args(args)
        return parsed_args

    def run(self, args):
        args = self.parse_args(args)
        self.create_car(path=args.path, template=args.template, overwrite=args.overwrite)

    def create_car(self, path, template='donkey2', overwrite=False):
        """
        This script sets up the folder struction for donkey to work.
        It must run without donkey installed so that people installing with
        docker can build the folder structure for docker to mount to.
        """

        # these are needed encase None is passed as path
        path = path or '~/mycar'
        template = template or 'donkey2'

        if os.path.exists(path) and not overwrite:
            print('Car app already exists. Delete it and rerun createcar to replace.')
        else:
            print("Copying car application template: {}".format(template))

            print("Creating car folder: {}".format(path))
            path = make_dir(path)

            print("Creating data & model folders.")
            folders = ['models', 'data', 'logs']
            folder_paths = [os.path.join(path, f) for f in folders]
            for fp in folder_paths:
                make_dir(fp)

            # add car application and config files if they don't exist
            template_path = self.find_template_path(template)

            print('template path: {}'.format(template_path))
            copy_tree(template_path, path)

        print("Donkey setup complete.")


    def find_template_path(self, template_name_or_path):
        """
        First try to find the named template. If it doesn't exist try to find the template if
        it were a path.
        :param template_name_or_path:
        :return: abs path of template or raise Value error if none found.
        """

        named_template_path = os.path.join(TEMPLATES_PATH, template_name_or_path)
        if os.path.exists(named_template_path):
            return named_template_path
        elif os.path.exists(template_name_or_path):
            return template_name_or_path
        else:
            raise ValueError('Could not find template. Looked in the following locations {}, {}.'.format(named_template_path, template_name_or_path))



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
    """
    This is the fuction linked to the "donkey" terminal command.
    """
    commands = {
            'createcar': CreateCar,
            'findcar': FindCar,
                }

    args = sys.argv[:]
    command_text = args[1]

    if command_text in commands.keys():
        command = commands[command_text]
        c = command()
        c.run(args[2:])
    else:
        dk.util.proc.eprint('Usage: The availible commands are:')
        dk.util.proc.eprint(list(commands.keys()))



