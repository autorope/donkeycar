"""
Assorted functions for manipulating data.
"""
import numpy as np
import itertools


def linear_bin(a):
    """
    Convert a value to a categorical array.

    Parameters
    ----------
    a : int or float
        A value between -1 and 1

    Returns
    -------
    list of int
        A list of length 15 with one item set to 1, which represents the linear value, and all other items set to 0.
    """
    a = a + 1
    b = round(a / (2 / 14))
    arr = np.zeros(15)
    arr[int(b)] = 1
    return arr


def linear_unbin(arr):
    """
    Convert a categorical array to value.

    See Also
    --------
    linear_bin
    """
    if not len(arr) == 15:
        raise ValueError('Illegal array length, must be 15')
    b = np.argmax(arr)
    a = b * (2 / 14) - 1
    return a


def bin_Y(Y):
    """
    Convert a list of values to a list of categorical arrays.

    Parameters
    ----------
    Y : iterable of int
        Iterable with values between -1 and 1

    Returns
    -------
    A two dimensional array of int

    See Also
    --------
    linear_bin
    """
    d = [ linear_bin(y) for y in Y ]
    return np.array(d)


def unbin_Y(Y):
    """
    Convert a list of categorical arrays to a list of values.

    See Also
    --------
    linear_bin
    """
    d = [ linear_unbin(y) for y in Y ]
    return np.array(d)


def map_range(x, X_min, X_max, Y_min, Y_max):
    """
    Linear mapping between two ranges of values
    """
    X_range = X_max - X_min
    Y_range = Y_max - Y_min
    XY_ratio = X_range / Y_range

    y = ((x - X_min) / XY_ratio + Y_min) // 1

    return int(y)


def merge_two_dicts(x, y):
    """
    Given two dicts, merge them into a new dict as a shallow copy
    """
    z = x.copy()
    z.update(y)
    return z


def param_gen(params):
    """
    Accepts a dictionary of parameter options and returns
    a list of dictionary with the permutations of the parameters.
    """
    for p in itertools.product(*params.values()):
        yield dict(zip(params.keys(), p ))
