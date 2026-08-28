#!/usr/bin/env python3
"""

Scripts to drive on autopilot using computer vision

Usage:
    manage.py (drive) [--js] [--log=INFO] [--camera=(single|stereo)] [--myconfig=<filename>] [--mcp]


Options:
    -h --help          Show this screen.
    --js               Use physical joystick.
    --mcp              Serve an MCP server so an AI agent can drive the car.
    --myconfig=filename     Specify myconfig file to use.
                            [default: myconfig.py]
"""

import logging
from typing import Any

from docopt import docopt
from simple_pid import PID

import donkeycar as dk
from donkeycar.parts.controller import JoystickController
from donkeycar.parts.datastore import TubHandler
from donkeycar.parts.explode import ExplodeDict
from donkeycar.parts.transform import Lambda
from donkeycar.parts.tub_v2 import TubWriter
from donkeycar.templates.complete import (
    DriveMode,
    ToggleRecording,
    UserPilotCondition,
    add_camera,
    add_drivetrain,
    add_simulator,
    add_user_controller,
)
from donkeycar.vehicle import Vehicle

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# `cfg` is a donkeycar.config.Config, which is populated by exec'ing the car's
# config.py, so its attributes do not exist statically. Annotating it as Any
# keeps the signatures honest instead of promising a shape mypy cannot check.
CarConfig = Any


def build_vehicle(
    cfg: CarConfig,
    use_joystick: bool = False,
    camera_type: str = "single",
    meta: list[str] | None = None,
    enable_mcp: bool = False,
) -> Vehicle:
    """
    Construct a working robotic vehicle from many parts, but do NOT start it.
    Each part runs as a job in the Vehicle loop, calling either
    it's run or run_threaded method depending on the constructor flag `threaded`.
    All parts are updated one after another at the framerate given in
    cfg.DRIVE_LOOP_HZ assuming each part finishes processing in a timely manner.
    Parts may have named outputs and inputs. The framework handles passing named outputs
    to parts requesting the same named input.

    Returns the assembled Vehicle so that a caller can decide how to run it.
    `drive()` starts it on the calling thread, which is what `manage.py drive`
    does. The MCP supervisor instead runs it on a background thread so that it
    can be stopped and rebuilt on request.
    """
    # Copy rather than mutate: this function may be called more than once in a
    # single process (the MCP supervisor rebuilds the vehicle on restart), and
    # the metadata list below is appended to.
    meta = list(meta) if meta else []

    # Initialize car
    V = dk.vehicle.Vehicle()

    #
    # if we are using the simulator, set it up
    #
    add_simulator(V, cfg)

    #
    # setup primary camera
    #
    add_camera(V, cfg, camera_type)

    #
    # add the user input controller(s)
    # - this will add the web controller
    # - it will optionally add any configured 'joystick' controller
    #
    has_input_controller = hasattr(cfg, "CONTROLLER_TYPE") and cfg.CONTROLLER_TYPE != "mock"
    ctr = add_user_controller(V, cfg, use_joystick, input_image="ui/image_array")

    #
    # explode the web buttons into their own key/values in memory
    #
    V.add(ExplodeDict(V.mem, "web/"), inputs=["web/buttons"])

    #
    # track user vs autopilot condition
    #
    V.add(
        UserPilotCondition(show_pilot_image=getattr(cfg, "OVERLAY_IMAGE", False)),
        inputs=["user/mode", "cam/image_array", "cv/image_array"],
        outputs=["run_user", "run_pilot", "ui/image_array"],
    )

    #
    # PID controller to be used with cv_controller
    #
    pid = PID(Kp=cfg.PID_P, Ki=cfg.PID_I, Kd=cfg.PID_D)

    def dec_pid_d() -> None:
        pid.Kd -= cfg.PID_D_DELTA
        logging.info("pid: d- %f", pid.Kd)

    def inc_pid_d() -> None:
        pid.Kd += cfg.PID_D_DELTA
        logging.info("pid: d+ %f", pid.Kd)

    def dec_pid_p() -> None:
        pid.Kp -= cfg.PID_P_DELTA
        logging.info("pid: p- %f", pid.Kp)

    def inc_pid_p() -> None:
        pid.Kp += cfg.PID_P_DELTA
        logging.info("pid: p+ %f", pid.Kp)

    #
    # Computer Vision Controller
    #
    add_cv_controller(
        V,
        cfg,
        pid,
        cfg.CV_CONTROLLER_MODULE,
        cfg.CV_CONTROLLER_CLASS,
        cfg.CV_CONTROLLER_INPUTS,
        cfg.CV_CONTROLLER_OUTPUTS,
        cfg.CV_CONTROLLER_CONDITION,
    )

    #
    # MCP bridge: carries agent intent into the loop and vehicle state back out.
    # It sits between the CV controller and DriveMode so that it can cap
    # pilot/throttle on the way through. Only added when asked for, so the
    # default pipeline is exactly the pipeline it has always been.
    #
    if enable_mcp:
        from donkeycar.parts.mcp_server import MCPBridge

        V.add(
            MCPBridge(cfg),
            inputs=["cam/image_array", "cv/image_array", "pilot/steering", "pilot/throttle", "user/mode"],
            outputs=["pilot/throttle", "mcp/lane_offset_px", "mcp/armed"],
            threaded=True,
        )

    recording_control = ToggleRecording(cfg.AUTO_RECORD_ON_THROTTLE, cfg.RECORD_DURING_AI)
    V.add(recording_control, inputs=["user/mode", "recording"], outputs=["recording"])

    #
    # Add buttons for handling various user actions
    # The button names are in configuration.
    # They may refer to game controller (joystick) buttons OR web ui buttons
    #
    # There are 5 programmable webui buttons, "web/w1" to "web/w5"
    # adding a button handler for a webui button
    # is just adding a part with a run_condition set to
    # the button's name, so it runs when button is pressed.
    #
    have_joystick = ctr is not None and isinstance(ctr, JoystickController)

    # button to toggle recording
    if cfg.TOGGLE_RECORDING_BTN:
        logger.info("Toggle recording button is %s", cfg.TOGGLE_RECORDING_BTN)
        if cfg.TOGGLE_RECORDING_BTN.startswith("web/w"):
            V.add(Lambda(lambda: recording_control.toggle_recording()), run_condition=cfg.TOGGLE_RECORDING_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.TOGGLE_RECORDING_BTN, recording_control.toggle_recording)

    # Buttons to tune PID constants
    if cfg.DEC_PID_P_BTN and cfg.PID_P_DELTA:
        logger.info("Decrement PID P button is %s", cfg.DEC_PID_P_BTN)
        if cfg.DEC_PID_P_BTN.startswith("web/w"):
            V.add(Lambda(dec_pid_p), run_condition=cfg.DEC_PID_P_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.DEC_PID_P_BTN, dec_pid_p)
    if cfg.INC_PID_P_BTN and cfg.PID_P_DELTA:
        logger.info("Increment PID P button is %s", cfg.INC_PID_P_BTN)
        if cfg.INC_PID_P_BTN.startswith("web/w"):
            V.add(Lambda(inc_pid_p), run_condition=cfg.INC_PID_P_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.INC_PID_P_BTN, inc_pid_p)
    if cfg.DEC_PID_D_BTN and cfg.PID_D_DELTA:
        logger.info("Decrement PID D button is %s", cfg.DEC_PID_D_BTN)
        if cfg.DEC_PID_D_BTN.startswith("web/w"):
            V.add(Lambda(dec_pid_d), run_condition=cfg.DEC_PID_D_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.DEC_PID_D_BTN, dec_pid_d)
    if cfg.INC_PID_D_BTN and cfg.PID_D_DELTA:
        logger.info("Increment PID D button is %s", cfg.INC_PID_D_BTN)
        if cfg.INC_PID_D_BTN.startswith("web/w"):
            V.add(Lambda(inc_pid_d), run_condition=cfg.INC_PID_D_BTN)
        elif have_joystick:
            ctr.set_button_down_trigger(cfg.INC_PID_D_BTN, inc_pid_d)

    #
    # Decide what inputs should change the car's steering and throttle
    # based on the choice of user or autopilot drive mode
    #
    V.add(
        DriveMode(cfg.AI_THROTTLE_MULT),
        inputs=["user/mode", "user/steering", "user/throttle", "pilot/steering", "pilot/throttle"],
        outputs=["steering", "throttle"],
    )

    #
    # Setup drivetrain
    #
    add_drivetrain(V, cfg)

    #
    # OLED display setup
    #
    if cfg.USE_SSD1306_128_32:
        from donkeycar.parts.oled import OLEDPart

        auto_record_on_throttle = cfg.USE_JOYSTICK_AS_DEFAULT and cfg.AUTO_RECORD_ON_THROTTLE
        oled_part = OLEDPart(cfg.SSD1306_128_32_I2C_ROTATION, cfg.SSD1306_RESOLUTION, auto_record_on_throttle)
        V.add(oled_part, inputs=["recording", "tub/num_records", "user/mode"], outputs=[], threaded=True)

    #
    # add tub to save data
    #
    inputs = ["cam/image_array", "steering", "throttle"]

    types = ["image_array", "float", "float"]

    #
    # Create data storage part
    #
    tub_path = TubHandler(path=cfg.DATA_PATH).create_tub_path() if cfg.AUTO_CREATE_NEW_TUB else cfg.DATA_PATH
    meta += getattr(cfg, "METADATA", [])
    tub_writer = TubWriter(tub_path, inputs=inputs, types=types, metadata=meta)
    V.add(tub_writer, inputs=inputs, outputs=["tub/num_records"], run_condition="recording")

    if cfg.DONKEY_GYM:
        logger.info("You can now go to http://localhost:%d to drive your car.", cfg.WEB_CONTROL_PORT)
    else:
        logger.info("You can now go to <your hostname.local>:%d to drive your car.", cfg.WEB_CONTROL_PORT)
    if has_input_controller:
        logger.info("You can now move your controller to drive your car.")
        if isinstance(ctr, JoystickController):
            ctr.set_tub(tub_writer.tub)
            ctr.print_controls()

    return V


def drive(
    cfg: CarConfig,
    use_joystick: bool = False,
    camera_type: str = "single",
    meta: list[str] | None = None,
    enable_mcp: bool = False,
) -> Vehicle:
    """
    Assemble the vehicle and run it on the calling thread.
    This is the entry point used by `manage.py drive` and its behaviour is
    unchanged: it blocks until the loop stops or the user interrupts.
    """
    V = build_vehicle(cfg, use_joystick=use_joystick, camera_type=camera_type, meta=meta, enable_mcp=enable_mcp)

    #
    # run the vehicle
    #
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ, max_loop_count=cfg.MAX_LOOPS)

    return V


#
# Computer Vision Controller
#
def add_cv_controller(
    V: Vehicle,
    cfg: CarConfig,
    pid: PID,
    module_name: str = "donkeycar.parts.line_follower",
    class_name: str = "LineFollower",
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    run_condition: str = "run_pilot",
) -> None:
    """
    Import the configured computer-vision controller and add it to the vehicle.

    The controller is resolved by name so that it can be swapped from the car's
    config without editing this template.
    """
    if inputs is None:
        inputs = ["cam/image_array"]
    if outputs is None:
        outputs = ["pilot/steering", "pilot/throttle", "cv/image_array"]

    # __import__ the module
    module = __import__(module_name)

    # walk module path to get to module with class
    for attr in module_name.split(".")[1:]:
        module = getattr(module, attr)

    my_class = getattr(module, class_name)

    # add instance of class to vehicle
    V.add(my_class(pid, cfg), inputs=inputs, outputs=outputs, run_condition=run_condition)


if __name__ == "__main__":
    args = docopt(__doc__)
    cfg = dk.load_config(myconfig=args["--myconfig"])

    log_level = args["--log"] or "INFO"
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    logging.basicConfig(level=numeric_level)

    if args["drive"]:
        drive(
            cfg,
            use_joystick=args["--js"],
            camera_type=args["--camera"],
            enable_mcp=bool(args["--mcp"]),
        )
