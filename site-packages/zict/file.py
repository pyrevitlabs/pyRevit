from __future__ import absolute_import, division, print_function

import errno
import os
try:
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote

from .common import ZictBase


def _safe_key(key):
    """
    Escape key so as to be usable on all filesystems.
    """
    # Even directory separators are unsafe.
    return quote(key, safe='')


def _unsafe_key(key):
    """
    Undo the escaping done by _safe_key().
    """
    return unquote(key)


class File(ZictBase):
    """ Mutable Mapping interface to a directory

    Keys must be strings, values must be bytes

    Note this shouldn't be used for interprocess persistence, as keys
    are cached in memory.

    Parameters
    ----------
    directory: string
    mode: string, ('r', 'w', 'a'), defaults to 'a'

    Examples
    --------
    >>> z = File('myfile')  # doctest: +SKIP
    >>> z['x'] = b'123'  # doctest: +SKIP
    >>> z['x']  # doctest: +SKIP
    b'123'

    Also supports writing lists of bytes objects

    >>> z['y'] = [b'123', b'4567']  # doctest: +SKIP
    >>> z['y']  # doctest: +SKIP
    b'1234567'

    Or anything that can be used with file.write, like a memoryview

    >>> z['data'] = np.ones(5).data  # doctest: +SKIP
    """
    def __init__(self, directory, mode='a'):
        self.directory = directory
        self.mode = mode
        self._keys = set()
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        else:
            for n in os.listdir(self.directory):
                self._keys.add(_unsafe_key(n))

    def __str__(self):
        return '<File: %s, mode="%s", %d elements>' % (self.directory, self.mode, len(self))

    __repr__ = __str__

    def __getitem__(self, key):
        if key not in self._keys:
            raise KeyError(key)
        with open(os.path.join(self.directory, _safe_key(key)), 'rb') as f:
            return f.read()

    def __setitem__(self, key, value):
        with open(os.path.join(self.directory, _safe_key(key)), 'wb') as f:
            if isinstance(value, (tuple, list)):
                for v in value:
                    f.write(v)
            else:
                f.write(value)
        self._keys.add(key)

    def __contains__(self, key):
        return key in self._keys

    def keys(self):
        return iter(self._keys)

    __iter__ = keys

    def __delitem__(self, key):
        if key not in self._keys:
            raise KeyError(key)
        os.remove(os.path.join(self.directory, _safe_key(key)))
        self._keys.remove(key)

    def __len__(self):
        return len(self._keys)
