import os, sys
this_file_path = os.path.dirname(os.path.abspath(__file__))
proj_path = os.path.abspath(os.path.join(this_file_path, os.pardir))
sys.path.append(proj_path)
