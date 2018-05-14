"""
Assorted functions for manipulating data.
"""
import numpy as np


def linear_bin(a):
    """
    Convert a linear value to a categorical array of length 15.
    """
    a = a + 1
    b = round(a / (2 / 14))
    arr = np.zeros(15)
    arr[int(b)] = 1
    return arr


def linear_unbin(arr):
    b = np.argmax(arr)
    a = b * (2 / 14) - 1
    return a


def bin_Y(Y):
    d = []
    for y in Y:
        arr = np.zeros(15)
        arr[linear_bin(y)] = 1
        d.append(arr)
    return np.array(d)


def unbin_Y(Y):
    d = []
    for y in Y:
        v = linear_unbin(y)
        d.append(v)
    return np.array(d)


def map_range(x, X_min, X_max, Y_min, Y_max):
    '''
    Linear mapping between two ranges of values
    '''
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range / Y_range

    y = ((x - X_min) / XY_ratio + Y_min) // 1

    return int(y)

'''
OTHER
'''
def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z



def param_gen(params):
    '''
    Accepts a dictionary of parameter options and returns
    a list of dictionary with the permutations of the parameters.
    '''
    for p in itertools.product(*params.values()):
        yield dict(zip(params.keys(), p ))