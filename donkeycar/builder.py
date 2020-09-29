import yaml
from donkeycar.parts import PartFactory
from donkeycar import Vehicle


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
                part_args = part_params['parameters']
                # this creates the part
                vehicle_part = PartFactory.make(part_name, part_args)
                inputs = part_params['inputs']
                outputs = part_params['outputs']
                threaded = part_params.get('threaded', False)
                run_condition = None
                # adding part to vehicle
                car.add(vehicle_part, inputs=inputs, outputs=outputs,
                        threaded=threaded, run_condition=run_condition)

        return car
