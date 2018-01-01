from __future__ import absolute_import, division, print_function

from collections import MutableMapping
import sys
import zipfile


class Zip(MutableMapping):
    """ Mutable Mapping interface to a Zip file

    Keys must be strings, values must be bytes

    Parameters
    ----------
    filename: string
    mode: string, ('r', 'w', 'a'), defaults to 'a'

    Examples
    --------
    >>> z = Zip('myfile.zip')  # doctest: +SKIP
    >>> z['x'] = b'123'  # doctest: +SKIP
    >>> z['x']  # doctest: +SKIP
    b'123'
    >>> z.flush()  # flush and write metadata to disk  # doctest: +SKIP
    """
    def __init__(self, filename, mode='a'):
        self.filename = filename
        self.mode = mode
        self._file = None

    @property
    def file(self):
        if self.mode == 'closed':
            raise IOError("File closed")
        if not self._file or not self._file.fp:
            self._file = zipfile.ZipFile(self.filename, mode=self.mode)
        return self._file

    def __getitem__(self, key):
        return self.file.read(key)

    def __setitem__(self, key, value):
        self.file.writestr(key, to_bytes(value))

    def keys(self):
        return (zi.filename for zi in self.file.filelist)

    def values(self):
        return map(self.file.read, self.keys())

    def items(self):
        return ((zi.filename, self.file.read(zi.filename))
                for zi in self.file.filelist)

    def __iter__(self):
        return self.keys()

    def __delitem__(self, key):
        raise NotImplementedError("Not supported by stdlib zipfile")

    def __len__(self):
        return len(self.file.filelist)

    def flush(self):
        self.file.fp.flush()
        self.file.close()

    def close(self):
        self.flush()
        self.mode = 'closed'

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


if sys.version_info[0] == 2:
    def to_bytes(x):
        if isinstance(x, bytearray):
            return bytes(x)
        return x
else:
    to_bytes = lambda x: x
