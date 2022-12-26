import os
import platform
import subprocess
import sys
import tarfile

from donkeycar import utils
import pytest


def is_error(err):
    for e in err:
        # Catch error if 'Error' is in the stderr output.
        if 'Error' in e.decode():
            return True
        # Catch error when the wrong command is used.
        if 'Usage:' in e.decode():
            return True
    return False


@pytest.fixture
def cardir(tmpdir_factory):
    path = tmpdir_factory.mktemp('mycar')
    return path


def test_createcar(cardir):
    cmd = ['donkey', 'createcar', '--path', cardir]
    out, err, proc_id = utils.run_shell_command(cmd)
    assert is_error(err) is False


def test_drivesim(cardir):
    cmd = ['donkey', 'createcar', '--path', cardir ,'--template', 'square']
    out, err, proc_id = utils.run_shell_command(cmd, timeout=10)
    cmd = ['python', 'manage.py', 'drive']
    out, err, proc_id = utils.run_shell_command(cmd, cwd=cardir)
    print(err)

    if is_error(err) is True:
        print('out', out)
        print('error: ', err)
        raise ValueError(err)


def test_bad_command_fails():
    cmd = ['donkey', 'not a comand']
    out, err, proc_id = utils.run_shell_command(cmd)
    print(err)
    print(out)
    assert is_error(err) is True


def test_tubplot(cardir):
    # create empy KerasLinear model in car directory
    model_dir = os.path.join(cardir, 'models')
    os.mkdir(model_dir)
    model_path = os.path.join(model_dir, 'model.h5')
    from donkeycar.parts.keras import KerasLinear
    KerasLinear().interpreter.model.save(model_path)

    # extract tub.tar.gz into car_dir/tub
    this_dir = os.path.dirname(os.path.abspath(__file__))
    with tarfile.open(os.path.join(this_dir, 'tub', 'tub.tar.gz')) as file:
        file.extractall(cardir)
    # define the tub dir
    tub_dir = os.path.join(cardir, 'tub')
    # put a dummy config file into the car dir
    cfg_file = os.path.join(cardir, 'config.py')
    with open(cfg_file, "w+") as f:
        f.writelines(["# config file\n", "IMAGE_H = 120\n", "IMAGE_W = 160\n",
                      "IMAGE_DEPTH = 3\n", "\n"])
    cmd = ['donkey', 'tubplot', '--tub', tub_dir, '--model', model_path,
           '--type', 'linear', '--noshow']

    # run donkey command in subprocess
    with subprocess.Popen(cmd, cwd=cardir, stdout=subprocess.PIPE) as pipe:
        line = '\nStart test: \n'
        while line:
            print(line, end='')
            line = pipe.stdout.readline().decode()
    print(f'List model dir: {os.listdir(model_dir)}')
    assert os.path.exists(model_path + '_pred.png')

