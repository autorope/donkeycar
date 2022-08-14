#
# part that executes a no-arg method when a button is clicked
#


class ExplodeDict:
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
