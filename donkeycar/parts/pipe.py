class Pipe:
    """
    Just pipe all inputs to the output, so they can be renamed.
    """
    def __init__(self):
        self.running = True

    def run(self, *args):
        if self.running:
            return args

    def shutdown(self):
        self.running = False
