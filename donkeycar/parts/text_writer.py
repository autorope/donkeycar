import logging
import os

logger = logging.getLogger(__name__)


class TextLogger:
    """
    Log data to a text file.
    A 'row' ends up as one line of text when transformed by row_to_line().
    The base implementation simply treats is as a text line, but subclasses
    an overwrite row_to_line() and line_to_row() to save structured data,
    like tuples or arrays as CSV.
    """
    def __init__(self, file_path:str, append:bool=False, allow_empty_file:bool=False, allow_empty_line:bool=True):
        self.file_path = file_path
        self.append = append
        self.allow_empty_file = allow_empty_file
        self.allow_empty_line = allow_empty_line
        self.rows = []

    def run(self, recording, rows):
        if recording and len is not None and len(rows) > 0:
            self.rows += rows
        return self.rows

    def length(self):
        return len(self.rows)

    def is_empty(self):
        return 0 == self.length()

    def is_loaded(self):
        return not self.is_empty()

    def get(self, row_index:int):
        return self.rows[row_index] if (row_index >= 0) and (row_index < self.length()) else None

    def reset(self):
        self.rows = []
        return True

    def row_to_line(self, row):
        """
        convert a row into a string
        """
        if row is not None:
            line = str(row)
            if self.allow_empty_line or len(line) > 0:
                return line
        return None

    def line_to_row(self, line:str):
        """
        convert a string into a row object
        """
        if isinstance(line, str):
            line = line.rstrip('\n')
            if self.allow_empty_line or len(line) > 0:
                return line
        return None

    def save(self):
        if self.is_loaded() or self.allow_empty_file:
            with open(self.file_path, "a" if self.append else "w") as fp:
                for row in self.rows:
                    line = self.row_to_line(row)
                    if line is not None:
                        fp.write(self.row_to_line(row))
                        fp.write('\n')
            return True
        return False

    def load(self):
        if os.path.exists(self.file_path):
            rows = []
            with open(self.file_path, "r") as file:
                for line in file:
                    row = self.line_to_row(line)
                    if row is not None:
                        rows.append(row)
            if rows or self.allow_empty_file:
                self.rows = rows
                return True
        return False


class CsvLogger(TextLogger):
    """
    Log iterable to a comma-separated text file.
    The separator can be customized.
    """
    def __init__(self, file_path:str, append:bool=False, allow_empty_file:bool=False, allow_empty_line:bool=True, separator:str=",", field_count:int=None, trim:bool=True):
        super().__init__(file_path, append, allow_empty_file, allow_empty_line)
        self.separator = separator
        self.field_count = field_count
        self.trim = trim

    def row_to_line(self, row):
        """
        convert a row into a string
        """
        if row is not None:
            line = self.separator.join([str(field) for field in row])
            if self.allow_empty_line or len(line) > 0:
                return line
        return None

    def line_to_row(self, line:str):
        """
        convert a string into a row object
        """
        row = None
        if isinstance(line, str):
            row = line.rstrip('\n').split(self.separator)
            field_count = len(row)
            if self.field_count is None or field_count == self.field_count:
                if self.trim:
                    row = [field.strip() for field in row]
            else:
                row = None
                logger.debug(f"CsvLogger: dropping row with field count = {field_count}")
        else:
            logging.error("CsvLogger: line_to_row expected string")
        return row
