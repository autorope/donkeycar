
from donkeycar.management import base
from tempfile import tempdir

def get_test_tub_path():
    tempdir()

def test_tubcheck():
    tc = base.TubCheck()
