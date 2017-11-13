from donkeycar import utils
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


def test_createcar(tmpdir):
    p = tmpdir.mkdir("d2")
    cmd = ['donkey', 'createcar', '--path', p]
    out, err, proc_id = utils.run_shell_command(cmd)
    assert is_error(err) is False


def test_drivesim(tmpdir):
    p = tmpdir.mkdir("d2")
    cmd = ['donkey', 'createcar', '--path', p ,'--template', 'square']
    out, err, proc_id = utils.run_shell_command(cmd, timeout=10)
    cmd = ['python', 'manage.py', 'drive']
    out, err, proc_id = utils.run_shell_command(cmd, cwd = p)
    print(err)

    if is_error(err) is True:
        print('out', out)
        print('error: ', err)
        raise ValueError (err)

def test_bad_command_fails(tmpdir):
    p = tmpdir.mkdir("d2")
    cmd = ['donkey', 'not a comand']
    out, err, proc_id = utils.run_shell_command(cmd)
    print(err)
    print(out)
    assert is_error(err) is True

## create car




## drive car