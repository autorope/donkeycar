class Pipe:
    """
    Just pipe all inputs to the output, so they can be renamed.
    """
    def run(self, *args):
        # seems to be a python bug that takes a single argument
        # return makes it into two element tuple with empty last element.
        return args if len(args) > 1 else args[0]
