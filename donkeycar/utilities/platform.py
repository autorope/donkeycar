import os
import platform

#
# functions to query hardware and os
#


def is_mac():
    """
    True if running on MacOs
    """
    return "Darwin" == platform.system()


def is_windows():
    """
    True if running on Windows operating system.
    """
    return "Windows" == platform.system()


def is_linux():
    """
    True for any linux OS
    """
    return "Linux" == platform.system()


# TODO: create is_raspberrypi() - true if running on raspberrypi


#
# read tegra chip id if it exists.
#
def _read_chip_id() -> str:
    """
    Read the tegra chip id.
    On non-tegra platforms this will be blank.
    """
    try:
        with open("/sys/module/tegra_fuse/parameters/tegra_chip_id", "r") as f:
            return next(f)
    except FileNotFoundError:
        pass
    return ""

_chip_id = None

def is_jetson() -> bool:
    """
    Determine if platform is a jetson
    """
    global _chip_id
    if _chip_id is None:
        _chip_id = _read_chip_id()
    return _chip_id != ""
