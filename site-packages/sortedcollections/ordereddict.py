"""Ordered dictionary implementation.

"""

import collections as co
from itertools import count
from operator import eq
import sys

from sortedcontainers import SortedDict
from sortedcontainers.sortedlist import recursive_repr

if sys.hexversion < 0x03000000:
    from itertools import imap # pylint: disable=wrong-import-order, ungrouped-imports
    map = imap # pylint: disable=redefined-builtin, invalid-name

NONE = object()


class KeysView(co.KeysView):
    "Read-only view of mapping keys."
    # pylint: disable=too-few-public-methods
    def __reversed__(self):
        "``reversed(keys_view)``"
        return reversed(self._mapping)


class ItemsView(co.ItemsView):
    "Read-only view of mapping items."
    # pylint: disable=too-few-public-methods
    def __reversed__(self):
        "``reversed(items_view)``"
        for key in reversed(self._mapping):
            yield key, self._mapping[key]


class ValuesView(co.ValuesView):
    "Read-only view of mapping values."
    # pylint: disable=too-few-public-methods
    def __reversed__(self):
        "``reversed(values_view)``"
        for key in reversed(self._mapping):
            yield self._mapping[key]


class SequenceView(object):
    "Read-only view of mapping keys as sequence."
    # pylint: disable=too-few-public-methods
    def __init__(self, nums):
        self._nums = nums

    def __len__(self):
        "``len(sequence_view)``"
        return len(self._nums)

    def __getitem__(self, index):
        "``sequence_view[index]``"
        num = self._nums.iloc[index]
        return self._nums[num]


class OrderedDict(dict):
    """Dictionary that remembers insertion order and is numerically indexable.

    Keys are numerically indexable using the ``iloc`` attribute. For example::

        >>> ordered_dict = OrderedDict.fromkeys('abcde')
        >>> ordered_dict.iloc[0]
        'a'
        >>> ordered_dict.iloc[-2:]
        ['d', 'e']

    The ``iloc`` attribute behaves as a sequence-view for the mapping.

    """
    # pylint: disable=super-init-not-called
    def __init__(self, *args, **kwargs):
        self._keys = {}
        self._nums = nums = SortedDict()
        self._count = count()
        self.iloc = SequenceView(nums)
        self.update(*args, **kwargs)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        "``ordered_dict[key] = value``"
        if key not in self:
            num = next(self._count)
            self._keys[key] = num
            self._nums[num] = key
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        "``del ordered_dict[key]``"
        dict_delitem(self, key)
        num = self._keys.pop(key)
        del self._nums[num]

    def __iter__(self):
        "``iter(ordered_dict)``"
        return self._nums.itervalues()

    def __reversed__(self):
        "``reversed(ordered_dict)``"
        nums = self._nums
        for key in reversed(nums):
            yield nums[key]

    def clear(self, dict_clear=dict.clear):
        "Remove all items from mapping."
        dict_clear(self)
        self._keys.clear()
        self._nums.clear()

    def popitem(self, last=True):
        """Remove and return (key, value) item pair.

        Pairs are returned in LIFO order if last is True or FIFO order if
        False.

        """
        index = -1 if last else 0
        num = self._nums.iloc[index]
        key = self._nums[num]
        value = self.pop(key)
        return key, value

    update = __update = co.MutableMapping.update

    def keys(self):
        "List of keys in mapping."
        return list(self.iterkeys())

    def items(self):
        "List of (key, value) item pairs in mapping."
        return list(self.iteritems())

    def values(self):
        "List of values in mapping."
        return list(self.itervalues())

    def iterkeys(self):
        "Return iterator over the keys in mapping."
        return self._nums.itervalues()

    def iteritems(self):
        "Return iterator over the (key, value) item pairs in mapping."
        for key in self._nums.itervalues():
            yield key, self[key]

    def itervalues(self):
        "Return iterator over the values in mapping."
        for key in self._nums.itervalues():
            yield self[key]

    def viewkeys(self):
        "Return set-like object with view of mapping keys."
        return KeysView(self)

    def viewitems(self):
        "Return set-like object with view of mapping items."
        return ItemsView(self)

    def viewvalues(self):
        "Return object with view of mapping values."
        return ValuesView(self)

    def pop(self, key, default=NONE):
        """Remove given key and return corresponding value.

        If key is not found, default is returned if given, otherwise raise
        KeyError.

        """
        if key in self:
            value = self[key]
            del self[key]
            return value
        elif default is NONE:
            raise KeyError(key)
        else:
            return default

    def setdefault(self, key, default=None):
        """Return ``mapping.get(key, default)``, also set ``mapping[key] = default`` if
        key not in mapping.

        """
        if key in self:
            return self[key]
        self[key] = default
        return default

    @recursive_repr
    def __repr__(self):
        "Text representation of mapping."
        return '%s(%r)' % (self.__class__.__name__, self.items())

    __str__ = __repr__

    def __reduce__(self):
        "Support for pickling serialization."
        return (self.__class__, (self.items(),))

    def copy(self):
        "Return shallow copy of mapping."
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        """Return new mapping with keys from iterable.

        If not specified, value defaults to None.

        """
        return cls((key, value) for key in iterable)

    def __eq__(self, other):
        "Test self and other mapping for equality."
        if isinstance(other, OrderedDict):
            return dict.__eq__(self, other) and all(map(eq, self, other))
        else:
            return dict.__eq__(self, other)

    __ne__ = co.MutableMapping.__ne__

    def _check(self):
        "Check consistency of internal member variables."
        # pylint: disable=protected-access
        keys = self._keys
        nums = self._nums

        for key, value in keys.items():
            assert nums[value] == key

        nums._check()
