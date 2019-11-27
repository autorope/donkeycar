import pytest
import time

from donkeycar import utils
from donkeycar.parts.launch import *


def test_ai_launch():
    ai_launch = AiLaunch(launch_duration=1.0, launch_throttle=1.0)

    mode = "user"
    ai_throttle = 0.0

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 0.0)

    mode = "local"

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 0.0)

    mode = "user"

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 0.0)

    ai_launch.enable_ai_launch()
    mode = "local"

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 1.0)

    time.sleep(1.1)

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 0.0)


def test_ai_launch_keep_enabled():
    ai_launch = AiLaunch(launch_duration=1.0, launch_throttle=1.0, keep_enabled=True)

    mode = "user"
    ai_throttle = 0.0

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 0.0)

    mode = "local"

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 1.0)

    new_throttle = ai_launch.run(mode, ai_throttle)

    time.sleep(1.1)

    new_throttle = ai_launch.run(mode, ai_throttle)
    assert(new_throttle == 0.0)

    mode = "user"

    new_throttle = ai_launch.run(mode, ai_throttle)
    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(ai_launch.enabled==False)
    assert(new_throttle == 0.0)

    mode = "local"

    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 1.0)

    time.sleep(1.1)

    new_throttle = ai_launch.run(mode, ai_throttle)

    mode = "user"

    new_throttle = ai_launch.run(mode, ai_throttle)
    new_throttle = ai_launch.run(mode, ai_throttle)

    assert(new_throttle == 0.0)

