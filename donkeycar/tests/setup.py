import os
import platform
import pytest
from donkeycar.parts.datastore import Tub
from donkeycar.parts.simulation import SquareBoxCamera, MovingSquareTelemetry
from donkeycar.management.base import CreateCar

def on_pi():
    if 'arm' in platform.machine():
        return True
    return False

temp_tub_path = None

@pytest.fixture
def tub_path(tmpdir):
    tub_path = tmpdir.mkdir('tubs').join('tub')
    return str(tub_path)

@pytest.fixture
def tub(tub_path):
    t = create_sample_tub(tub_path, records=128)
    return t

@pytest.fixture
def tubs(tmpdir, tubs=5):
    tubs_dir = tmpdir.mkdir('tubs')
    tub_paths = [ str(tubs_dir.join('tub_{}'.format(i))) for i in range(tubs) ]
    tubs = [ create_sample_tub(tub_path, records=5) for tub_path in tub_paths ]
    return (str(tubs_dir), tub_paths, tubs)
    
def create_sample_tub(path, records=128):
    inputs=['cam/image_array', 'user/angle', 'user/throttle']
    types=['image_array', 'float', 'float']
    t = Tub(path, inputs=inputs, types=types)
    cam = SquareBoxCamera()
    tel = MovingSquareTelemetry()
    for _ in range(records):
        x, y = tel.run()
        img_arr = cam.run(x, y)
        t.put_record({'cam/image_array': img_arr, 'user/angle': x, 'user/throttle':y})

    global temp_tub_path
    temp_tub_path = t
    print("setting temp tub path to:", temp_tub_path)

    return t

def d2_path(temp_path):
    path = os.path.join(temp_path, 'd2')
    return str(path)

def default_template(d2_path):
    c = CreateCar()
    c.create_car(d2_path, overwrite=True)
    return d2_path

def custom_template(d2_path, template):
    c = CreateCar()
    c.create_car(d2_path, template=template, overwrite=True)
    return d2_path


def create_sample_record():
    cam = SquareBoxCamera()
    tel = MovingSquareTelemetry()
    x, y = tel.run()
    img_arr = cam.run(x, y)
    return {'cam/image_array': img_arr, 'angle': x, 'throttle':y}