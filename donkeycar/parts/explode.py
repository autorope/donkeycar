#
# part that explodes a dictionary argument into individually named arguments
#


class ExplodeDict:
    """
    part that expands a dictionary input argument
    into individually named output arguments
    """
    def __init__(self, memory, output_prefix = ""):
        """
        Break a map into key/value pairs and write
        them to the output memory, optionally
        prefixing the key on output.
        Basically, take a dictionary and write
        it to the output.
        """
        self.memory = memory
        self.prefix = output_prefix

    def run(self, key_values):
        if type(key_values) is dict:
            for key, value in key_values.items():
                self.memory[self.prefix + key] = value
        return None
