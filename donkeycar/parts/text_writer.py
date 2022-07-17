import logging

logger = logging.getLogger(__name__)


class TextWriter:
    """
    Write lines to a text file
    """
    def __init__(self, filepath:str,  eol:str = None):
        self.filepath = filepath
        self.eol = eol
        self.fp = open(filepath, "w")

    def run(self, lines):
        if lines is not None and self.fp is not None:
            for line in lines:
                try:
                    self.fp.write(str(line))
                    if self.eol:
                        self.fp.write(self.eol)
                except IOError as e:
                    logger.error(f"Error while writing line to text file: ${e}")

    def shutdown(self):
        if self.fp:
            self.fp.flush()
            self.fp.close()
            self.fp = None


class CsvWriter:
    """
    Write list of iterables to a comma separated values file
    """
    def __init__(self, filepath:str, separator:str=",", eol:str = None):
        self.filepath = filepath
        self.separator = separator
        self.eol = eol
        self.fp = open(filepath, "w")

    def run(self, rows):
        if rows is not None and self.fp is not None:
            for row in rows:
                try:
                    separator = None # don't write separator before first field
                    for field in row:
                        if separator:
                            self.fp.write(separator)
                        self.fp.write(str(field).strip())
                        separator = self.separator
                    if self.eol:
                        self.fp.write(self.eol)
                except IOError as e:
                    logger.error(f"Error while writing line to csv file: ${e}")

    def shutdown(self):
        if self.fp:
            self.fp.flush()
            self.fp.close()
            self.fp = None
