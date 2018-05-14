from donkeycar.parts.transform import Lambda


def f(a):
    return a + 1

def f2(a, b):
    return a + b + 1

def test_lambda_one_arg():
    l = Lambda(f)
    b = l.run(1)
    assert b == 2

def test_lambda_two_args():
    l = Lambda(f2)
    b = l.run(1, 1)
    assert b == 3
