from __future__ import absolute_import, division, print_function

from .common import ZictBase, close


class Func(ZictBase):
    """ Buffer a MutableMapping with a pair of input/output functions

    Parameters
    ----------
    dump: callable
        Function to call on value as we set it into the mapping
    load: callable
        Function to call on value as we pull it from the mapping
    d: MutableMapping

    Examples
    --------
    >>> def double(x):
    ...     return x * 2

    >>> def halve(x):
    ...     return x / 2

    >>> d = dict()
    >>> f = Func(double, halve, d)
    >>> f['x'] = 10
    >>> d
    {'x': 20}
    >>> f['x']
    10.0
    """
    def __init__(self, dump, load, d):
        self.dump = dump
        self.load = load
        self.d = d

    def __getitem__(self, key):
        return self.load(self.d[key])

    def __setitem__(self, key, value):
        self.d[key] = self.dump(value)

    def __contains__(self, key):
        return key in self.d

    def __delitem__(self, key):
        del self.d[key]

    def keys(self):
        return self.d.keys()

    def values(self):
        return map(self.load, self.d.values())

    def items(self):
        return ((k, self.load(v)) for k, v in self.d.items())

    def _do_update(self, items):
        self.d.update((k, self.dump(v)) for k, v in items)

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def __str__(self):
        return '<Func: %s<->%s %s>' % (funcname(self.dump),
                                       funcname(self.load),
                                       str(self.d))

    __repr__ = __str__

    def flush(self):
        self.d.flush()

    def close(self):
        close(self.d)


def funcname(func):
    """Get the name of a function."""
    while hasattr(func, 'func'):
        func = func.func
    try:
        return func.__name__
    except:
        return str(func)
