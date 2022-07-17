import logging
from typing import List, Set, Dict, Tuple, Optional


class LoggerPart:
    """
    Log the given values in vehicle memory.
    """
    def __init__(self, inputs: List[str], level: str="INFO", rate: int=1, logger=None):
        self.inputs = inputs
        self.rate = rate
        self.level = logging._nameToLevel.get(level, logging.INFO)
        self.logger = logging.getLogger(logger if logger is not None else "LoggerPart")

        self.values = {}
        self.count = 0
        self.running = True

    def run(self, *args):
        if self.running and args is not None and len(args) == len(self.inputs):
            self.count = (self.count + 1) % (self.rate + 1)
            for i in range(len(self.inputs)):
                field = self.inputs[i]
                value = args[i]
                old_value = self.values.get(field)
                if old_value != value:
                    # always log changes
                    self.logger.log(self.level, f"{field} = {old_value} -> {value}")
                    self.values[field] = value
                elif self.count >= self.rate:
                    self.logger.log(self.level, f"{field} = {value}")

    def shutdown(self):
        self.running = False
