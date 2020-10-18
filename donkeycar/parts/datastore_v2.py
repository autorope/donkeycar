import json
import os
import time
from pathlib import Path


NEWLINE = '\n'
NEWLINE_STRIP = '\r\n'
NEWLINE_LENGTH = len(NEWLINE)


class Seekable(object):
    '''
    A seekable file reader, writer which deals with newline delimited records. \n
    This reader maintains an index of line lengths, so seeking a line is a O(1) operation.
    '''

    def __init__(self, file, method='a+', line_lengths=list()):
        self.method = method
        self.line_lengths = list()
        self.cumulative_lengths = list()
        self.file = open(file, self.method, newline=NEWLINE)
        self.total_length = 0
        if len(line_lengths) <= 0:
            self._read_contents()
        else:
            self.line_lengths.extend(line_lengths)
            for line_length in self.line_lengths:
                self.total_length += line_length
                self.cumulative_lengths.append(self.total_length)

    def _read_contents(self):
        self.line_lengths.clear()
        self.cumulative_lengths.clear()
        self.total_length = 0
        self.file.seek(0)
        contents = self.file.readline()
        while len(contents) > 0:
            line_length = len(contents)
            self.line_lengths.append(line_length)
            self.total_length += line_length
            self.cumulative_lengths.append(self.total_length)
            contents = self.file.readline()
        self.seek_end_of_file()

    def __enter__(self):
        return self

    def writeline(self, contents):
        has_newline = contents[-1 * NEWLINE_LENGTH] == NEWLINE
        if has_newline:
            line = contents
        else:
            line = f'{contents}{NEWLINE}'

        offset = len(line)
        self.total_length += offset
        self.line_lengths.append(offset)
        self.cumulative_lengths.append(self.total_length)
        self.file.write(line)
        self.file.flush()

    def _line_start_offset(self, line_number):
        return self._offset_until(line_number - 1)

    def _line_end_offset(self, line_number):
        return self._offset_until(line_number)

    def _offset_until(self, line_index):
        end_index = line_index - 1
        return self.cumulative_lengths[end_index] if end_index >= 0 and end_index < len(self.cumulative_lengths) else 0

    def readline(self):
        contents = self.file.readline()
        return contents.rstrip(NEWLINE_STRIP)

    def seek_line_start(self, line_number):
        self.file.seek(self._line_start_offset(line_number))

    def seek_end_of_file(self):
        self.file.seek(self.total_length)

    def truncate_until_end(self, line_number):
        self.line_lengths = self.line_lengths[:line_number]
        self.cumulative_lengths = self.cumulative_lengths[:line_number]
        self.total_length = self.cumulative_lengths[-1] if len(self.cumulative_lengths) > 0 else 0
        self.seek_end_of_file()
        self.file.truncate()
    
    def read_from(self, line_number):
        current_offset = self.file.tell()
        self.seek_line_start(line_number)
        lines = list()
        contents = self.readline()
        while len(contents) > 0:
            lines.append(contents)
            contents = self.readline()
        
        self.file.seek(current_offset)
        return lines
    
    def update_line(self, line_number, contents):
        lines = self.read_from(line_number)
        length = len(lines)
        self.truncate_until_end(line_number - 1)
        self.writeline(contents)
        if length > 1:
            for line in lines[1:]:
                self.writeline(line)

    def lines(self):
        return len(self.line_lengths)

    def has_content(self):
        return self.lines() > 0

    def close(self):
        self.file.flush()
        self.file.close()

    def __exit__(self, type, value, traceback):
        self.close()


class Catalog(object):
    '''
    A new line delimited file that has records delimited by newlines. \n

    [ json object record ] \n
    [ json object record ] \n
    ...
    '''
    def __init__(self, path, start_index=0):
        self.path = Path(os.path.expanduser(path))
        self.manifest = CatalogMetadata(self.path, start_index=start_index)
        self.seekable = Seekable(self.path.as_posix(), line_lengths=self.manifest.line_lengths())

    def _exit_handler(self):
        self.close()

    def write_record(self, record):
        # Add record and update manifest
        contents = json.dumps(record, allow_nan=False, sort_keys=True)
        self.seekable.writeline(contents)
        line_lengths = self.seekable.line_lengths
        self.manifest.update_line_lengths(line_lengths)

    def close(self):
        self.manifest.close()
        self.seekable.close()


class CatalogMetadata(object):
    '''
    Manifest for a Catalog
    '''
    def __init__(self, catalog_path, start_index=0):
        path = Path(catalog_path)
        manifest_name = '%s.catalog_manifest' % (path.stem)
        self.manifest_path = Path(os.path.join(path.parent.as_posix(), manifest_name))
        self.seekeable = Seekable(self.manifest_path)
        has_contents = False
        if os.path.exists(self.manifest_path) and self.seekeable.has_content():
            self.seekeable.seek_line_start(1)
            contents = self.seekeable.readline()
            if contents:
                self.contents = json.loads(contents)
                has_contents = True

        if not has_contents:
            # New catalog metadata entry
            self.contents = dict()
            self.contents['path'] = self.manifest_path.name
            created_at = time.time()
            self.contents['created_at'] = created_at
            self.contents['start_index'] = start_index
            self.contents['line_lengths'] = list()
            self._update()

    def update_line_lengths(self, new_lengths):
        self.contents['line_lengths'] = new_lengths
        self._update()

    def line_lengths(self):
        return self.contents['line_lengths']

    def start_index(self):
        return self.contents['start_index']

    def _update(self):
        contents = json.dumps(self.contents, allow_nan=False, sort_keys=True)
        self.seekeable.truncate_until_end(0)
        self.seekeable.writeline(contents)

    def close(self):
        self.seekeable.close()


class Manifest(object):
    '''
    A newline delimited file, with the following format.

    [ json array of inputs ]\n
    [ json array of types ]\n
    [ json object with user metadata ]\n
    [ json object with manifest metadata ]\n
    [ json object with catalog metadata ]\n
    '''

    def __init__(self, base_path, inputs=[], types=[], metadata=[],
                 max_len=1000, read_only=False):
        self.base_path = Path(os.path.expanduser(base_path)).absolute()
        self.manifest_path = Path(os.path.join(self.base_path, 'manifest.json'))
        self.inputs = inputs
        self.types = types
        self._read_metadata(metadata)
        self.manifest_metadata = dict()
        self.max_len = max_len
        self.current_catalog = None
        self.current_index = 0
        self.catalog_paths = list()
        self.catalog_metadata = dict()
        self.deleted_indexes = set()
        has_catalogs = False

        if self.manifest_path.exists():
            self.seekeable = Seekable(self.manifest_path)
            if self.seekeable.has_content():
                self._read_contents()
            has_catalogs = len(self.catalog_paths) > 0
        else:
            created_at = time.time()
            self.manifest_metadata['created_at'] = created_at
            if not self.base_path.exists():
                self.base_path.mkdir(parents=True, exist_ok=True)
                print('Created a new datastore at %s' % (self.base_path.as_posix()))
            method = 'r' if read_only else 'a+'
            self.seekeable = Seekable(self.manifest_path, method=method)

        if not has_catalogs:
            self._write_contents()
            self._add_catalog()
        else:
            last_known_catalog = os.path.join(self.base_path, self.catalog_paths[-1]);
            print('Using catalog %s' % (last_known_catalog))
            self.current_catalog = Catalog(last_known_catalog, self.current_index)

    def write_record(self, record):
        new_catalog = self.current_index > 0 and (self.current_index % self.max_len) == 0
        if new_catalog:
            self._add_catalog()

        self.current_catalog.write_record(record)
        self.current_index += 1
        # Update metadata to keep track of the last index
        self._update_catalog_metadata(update=True)

    def delete_record(self, record_index):
        # Does not actually delete the record, but marks it as deleted.
        self.deleted_indexes.add(record_index)
        self._update_catalog_metadata(update=True)

    def _add_catalog(self):
        current_length = len(self.catalog_paths)
        catalog_name = 'catalog_%s.catalog' % (current_length)
        catalog_path = os.path.join(self.base_path, catalog_name)
        current_catalog = self.current_catalog
        self.current_catalog = Catalog(catalog_path, start_index=self.current_index)
        # Store relative paths
        self.catalog_paths.append(catalog_name)
        self._update_catalog_metadata(update=True)
        if current_catalog:
            current_catalog.close()

    def _read_metadata(self, metadata=[]):
        self.metadata = dict()
        for (key, value) in metadata:
            self.metadata[key] = value

    def _read_contents(self):
        self.seekeable.seek_line_start(1)
        self.inputs = json.loads(self.seekeable.readline())
        self.types = json.loads(self.seekeable.readline())
        self.metadata = json.loads(self.seekeable.readline())
        self.manifest_metadata = json.loads(self.seekeable.readline())
        # Catalog metadata
        catalog_metadata = json.loads(self.seekeable.readline())
        self.catalog_paths = catalog_metadata['paths']
        self.current_index = catalog_metadata['current_index']
        self.max_len = catalog_metadata['max_len']
        self.deleted_indexes = set(catalog_metadata['deleted_indexes'])

    def _write_contents(self):
        self.seekeable.truncate_until_end(0)
        self.seekeable.writeline(json.dumps(self.inputs))
        self.seekeable.writeline(json.dumps(self.types))
        self.seekeable.writeline(json.dumps(self.metadata))
        self.seekeable.writeline(json.dumps(self.manifest_metadata))
        self._update_catalog_metadata(update=False)

    def _update_catalog_metadata(self, update=True):
        if update:
            self.seekeable.truncate_until_end(4)
        # Catalog metadata
        catalog_metadata = dict()
        catalog_metadata['paths'] = self.catalog_paths
        catalog_metadata['current_index'] = self.current_index
        catalog_metadata['max_len'] = self.max_len
        catalog_metadata['deleted_indexes'] = list(self.deleted_indexes)
        self.catalog_metadata = catalog_metadata
        self.seekeable.writeline(json.dumps(catalog_metadata))

    def close(self):
        self.current_catalog.close()
        self.seekeable.close()

    def __iter__(self):
        return ManifestIterator(self)

    def __len__(self):
        # current_index is already pointing to the next index
        return self.current_index - len(self.deleted_indexes)


class ManifestIterator(object):
    '''
    An iterator for the Manifest type. \n

    Returns catalog entries lazily when a consumer calls __next__().
    '''
    def __init__(self, manifest):
        self.manifest = manifest
        self.has_catalogs = len(self.manifest.catalog_paths) > 0
        self.current_index = 0
        self.current_catalog_index = 0
        self.current_catalog = None

    def __next__(self):
        if not self.has_catalogs:
            raise StopIteration('No catalogs')

        if self.current_catalog_index >= len(self.manifest.catalog_paths):
            raise StopIteration('No more catalogs')

        if self.current_catalog is None:
            current_catalog_path = os.path.join(self.manifest.base_path, self.manifest.catalog_paths[self.current_catalog_index])
            self.current_catalog = Catalog(current_catalog_path)
            self.current_catalog.seekable.seek_line_start(1)

        contents = self.current_catalog.seekable.readline()

        if contents is not None and len(contents) > 0:
            # Check for current_index when we are ready to advance the underlying iterator.
            current_index = self.current_index
            self.current_index += 1
            if current_index in self.manifest.deleted_indexes:
                # Skip over index, because it has been marked deleted
                return self.__next__()
            else:
                try:
                    record = json.loads(contents)
                    return record
                except Exception:
                    print('Ignoring record at index %s' % (current_index))
                    return self.__next__() 
        else:
            self.current_catalog = None
            self.current_catalog_index += 1
            return self.__next__()

    next = __next__

    def __len__(self):
        return self.manifest.__len__()
