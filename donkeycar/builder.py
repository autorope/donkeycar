import yaml
from donkeycar.parts.part import PartFactory
from donkeycar import Vehicle
# -- !!! THIS import cannot be removed as otherwise the metaclass
# initialisation does not run for all parts !!!
from donkeycar.parts.camera import *


class Builder:
    def __init__(self, car_file='car.yaml'):
        self.car_file = car_file
        self.vehicle_hz = 20
        self.max_loop_count = None
        self.verbose = False

    def build_vehicle(self):
        with open(self.car_file) as f:
            obj_file = yaml.load(f, Loader=yaml.FullLoader)

        self.vehicle_hz = obj_file.get('vehicle_hz', 20)
        self.max_loop_count = obj_file.get('max_loop_count')
        self.verbose = obj_file.get('verbose', False)
        parts = obj_file.get('parts')
        car = Vehicle()

        for part in parts:
            for part_name, part_params in part.items():
                # we are using .get on part parameters here as the part might
                # might not require any
                part_args = part_params.get('parameters')
                # this creates the part
                vehicle_part = PartFactory.make(part_name, part_args)
                inputs = part_params.get('inputs', [])
                outputs = part_params.get('outputs', [])
                threaded = part_params.get('threaded', False)
                run_condition = None
                # adding part to vehicle
                car.add(vehicle_part, inputs=inputs, outputs=outputs,
                        threaded=threaded, run_condition=run_condition)

        return car, self.vehicle_hz, self.max_loop_count, self.verbose

