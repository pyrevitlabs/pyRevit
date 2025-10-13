"""Helper functions for python.

Examples:
    ```python
    from pyrevit.coreutils import pyutils
    pyutils.safe_cast('string', int, 0)
    ```
"""
#pylint: disable=C0103
import re
import copy
from itertools import tee
from collections import OrderedDict

from pyrevit.compat import PY2, Callable
if PY2:
    from itertools import izip as zip


class DefaultOrderedDict(OrderedDict):
    """Ordered dictionary with default type.

    This is similar to defaultdict and maintains the order of items added
    to it so in that regards it functions similar to OrderedDict.

    Examples:
        ```python
        from pyrevit.coreutils import pyutils
        od = pyutils.DefaultOrderedDict(list)
        od['A'] = [1, 2, 3]
        od['B'] = [4, 5, 6]
        od['C'].extend([7, 8, 9])
        for k, v in od.items():
            print(k, v)
        ```
        ('A', [1, 2, 3])
        ('B', [4, 5, 6])
        ('C', [7, 8, 9])
    """

    # Source: http://stackoverflow.com/a/6190500/562769
    def __init__(self, default_factory=None, *a, **kw): #pylint: disable=W1113

        if (default_factory is not None \
                and not isinstance(default_factory, Callable)):
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
            args = self.default_factory
        return type(self), args, None, None, self.items()

    def copy(self):
        """Copy the dictionary."""
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
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
        (Iterable[Any]): list of pairs

    Examples:
        ```python
        pairwise([1, 2, 3, 4, 5])
        ```
        [(1, 2), (3, 4)]    # 5 can not be paired
        ```python
        pairwise([1, 2, 3, 4, 5, 6])
        ```
        [(1, 2), (3, 4), (5, 6)]
        ```python
        pairwise([1, 2, 3, 4, 5, 6], step=1)
        ```
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]
    """
    if step == 1:
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)
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

    Examples:
        ```python
        safe_cast('name', int, default=0)
        ```
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
        (bool): True of token is int or float

    Examples:
        ```python
        isnumber('12.3')
        ```
        True
    """
    if token:
        return re.match("^-*[0-9.]+?$", token) is not None
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


def merge(d1, d2):
    """Merge d2 into d1.

    d2 dict values are recursively merged into d1 dict values
    other d2 values are added to d1 dict values with the same key
    new d2 values are added to d1
    d2 values override other d1 values

    Args:
        d1 (dict): dict to be updated
        d2 (dict): dict to be merge into d1

    Returns:
        (dict[Any, Any]): updated d1

    Examples:
        ```python
        d1 = {1: 1, 2: "B"    , 3: {1:"A", 2:"B"}, 4: "b"  , 5: ["a", "b"]}
        d2 = {1: 1, 2: {1:"A"}, 3: {1:"S", 3:"C"}, 4: ["a"], 5: ["c"]}
        merge(d1, d2)
        ```
        { 1:1,
          2:{1:'A', 2:'B'},
          3:{1:'S', 2:'B', 3:'C'},
          4:['a','b'],
          5: ['c', 'a', 'b']
        }
    """
    if not (isinstance(d1, dict) and isinstance(d2, dict)):
        raise Exception('Both inputs must be of type dict')

    for key, new_value in d2.items():
        if key in d1:
            old_value = d1[key]
            if isinstance(new_value, dict):
                if isinstance(old_value, dict):
                    merge(old_value, new_value)
                else:
                    new_dict = copy.deepcopy(new_value)
                    new_dict[key] = old_value
                    d1[key] = new_dict
            elif isinstance(old_value, dict):
                old_value[key] = new_value
            elif isinstance(new_value, list):
                new_list = copy.deepcopy(new_value)
                if isinstance(old_value, list):
                    new_list.extend(old_value)
                else:
                    if old_value not in new_value:
                        new_list.append(old_value)
                d1[key] = new_list
            elif isinstance(old_value, list):
                if new_value not in old_value:
                    old_value.append(new_value)
            else:
                d1[key] = new_value
        else:
            d1[key] = new_value
    return d1


def almost_equal(a, b, rnd=5):
    """Check if two numerical values almost equal.

    Args:
        a (float): value a
        b (float): value b
        rnd (int, optional): n digits after comma. Defaults to 5.

    Returns:
        (bool): True if almost equal
    """
    return a == b or int(a*10**rnd) == int(b*10**rnd)
