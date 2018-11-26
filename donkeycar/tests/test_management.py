
from donkeycar.management import base
from tempfile import tempdir

def get_test_tub_path():
    tempdir()

def test_findcar():
    fc = base.FindCar()
