"""Helper functions for python.

Example:
    >>> from pyrevit.coreutils import pyutils
    >>> pyutils.safe_cast('string', int, 0)
"""

import re
from collections import OrderedDict, Callable


class DefaultOrderedDict(OrderedDict):
    """Ordered dictionary with default type.

    This is similar to defaultdict and maintains the order of items added
    to it so in that regards it functions similar to OrderedDict.

    Example:
        >>> from pyrevit.coreutils import pyutils
        >>> od = pyutils.DefaultOrderedDict(list)
        >>> od['A'] = [1, 2, 3]
        >>> od['B'] = [4, 5, 6]
        >>> od['C'].extend([7, 8, 9])
        >>> for k, v in od.items():
        ...     print(k, v)
        ('A', [1, 2, 3])
        ('B', [4, 5, 6])
        ('C', [7, 8, 9])
    """

    # Source: http://stackoverflow.com/a/6190500/562769
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
           not isinstance(default_factory, Callable)):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        """Copy the dictionary."""
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    def __repr__(self, _repr_running=None):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               OrderedDict.__repr__(self))


def pairwise(iterable, step=2):
    """Iterate through items in pairs.

    Args:
        iterable (iterable): any iterable object
        step (int): number of steps to move when making pairs

    Returns:
        iterable: list of pairs

    Example:
        >>> pairwise([1, 2, 3, 4, 5])
        [(1, 2), (3, 4)]    # 5 can not be paired
        >>> pairwise([1, 2, 3, 4, 5, 6])
        [(1, 2), (3, 4), (5, 6)]
        >>> pairwise([1, 2, 3, 4, 5, 6], step=1)
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]
    """
    if step == 1:
        from itertools import tee, izip
        a, b = tee(iterable)
        next(b, None)
        return izip(a, b)
    elif step == 2:
        a = iter(iterable)
        return zip(a, a)


def safe_cast(val, to_type, default=None):
    """Convert value to type gracefully.

    This method basically calls to_type(value) and returns the default
    if exception occurs.

    Args:
        val (any): value to be converted
        to_type (type): target type
        default (any): value to rerun on conversion exception

    Example:
        >>> safe_cast('name', int, default=0)
        0
    """
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def isnumber(token):
    """Verify if given string token is int or float.

    Args:
        token (str): string value

    Returns:
        bool: True of token is int or float

    Example:
        >>> isnumber('12.3')
        True
    """
    if token:
        return re.match("^[0-9.]+?$", token) is not None
    else:
        return False


def compare_lists(x, y):
    """Compare two lists.

    See: https://stackoverflow.com/a/10872313/2350244

    Args:
        x (list): first list
        y (list): second list
    """
    return len(frozenset(x).difference(y)) == 0
