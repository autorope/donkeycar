#
# part that executes a no-arg method when a button is clicked
#


class UnzipDict:
    def __init__(self, prefix):
        """
        Break a map into key/value pairs and write
        them to the output memory
        """
    def run(self, key_values):
        if type(key_values) is dict:
            return tuple(key_values.values())
        return ()
