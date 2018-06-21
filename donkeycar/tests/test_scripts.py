from donkeycar import util
import pytest


def is_error(err):
    for e in err:
        #Catch error if 'Error' is in the stderr output.
        if 'Error' in e.decode():
            return True
        #Catch error when the wrong command is used.
        if 'Usage:' in e.decode():
            return True
    return False


@pytest.fixture
def cardir(tmpdir):
    path = str(tmpdir.mkdir("mycar"))
    return path


def test_createcar(cardir):
    cmd = ['donkey', 'createcar', '--path', cardir]
    out, err, proc_id = util.proc.run_shell_command(cmd)
    assert is_error(err) is False

def test_drivesim(cardir):
    cmd = ['donkey', 'createcar', '--path', cardir ,'--template', 'square']
    out, err, proc_id = util.proc.run_shell_command(cmd, timeout=10)
    cmd = ['python', 'manage.py', 'drive']
    out, err, proc_id = util.proc.run_shell_command(cmd, cwd = cardir)
    print(err)

    if is_error(err) is True:
        print('out', out)
        print('error: ', err)
        raise ValueError (err)

def test_bad_command_fails():
    cmd = ['donkey', 'not a comand']
    out, err, proc_id = util.proc.run_shell_command(cmd)
    print(err)
    print(out)
    assert is_error(err) is True
