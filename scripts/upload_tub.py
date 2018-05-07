import sys
from donkeycar.parts.datastore import TubUploader
import argparse

if __name__ == "__main__":
    def parse_args(args):
        print(args)
        parser = argparse.ArgumentParser(prog='upload_tub.py')
        parser.add_argument('path', type=str)
        parser.add_argument('--delete_when_uploaded', default=True, help='delete files after their uploaded')
        parsed_args = parser.parse_args(args)
        return parsed_args


    def run(args):
        args = parse_args(args)
        tu = TubUploader(1, path=args.path, delete_when_uploaded=args.delete_when_uploaded)
        tu.upload()


    run(args=sys.argv[1:])
