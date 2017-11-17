"""Sorted collections recipes implementations.

"""

import collections as co
from itertools import count
from sortedcontainers import SortedListWithKey, SortedDict, SortedSet
from sortedcontainers.sortedlist import recursive_repr


class IndexableDict(SortedDict):
    """Dictionary that supports numerical indexing.

    Keys are numerically indexable using the ``iloc`` attribute. For example::

        >>> indexable_dict = IndexableDict.fromkeys('abcde')
        >>> indexable_dict.keys()
        ['b', 'd', 'e', 'c', 'a']
        >>> indexable_dict.iloc[0]
        'b'
        >>> indexable_dict.iloc[-2:]
        ['c', 'a']

    The ``iloc`` attribute behaves as a sequence-view for the mapping.

    """
    def __init__(self, *args, **kwargs):
        super(IndexableDict, self).__init__(hash, *args, **kwargs)


class IndexableSet(SortedSet):
    """Set that supports numerical indexing.

    For example::

        >>> indexable_set = IndexableSet('abcde')
        >>> list(indexable_set)
        ['d', 'e', 'c', 'b', 'a']
        >>> indexable_set[0]
        'd'
        >>> indexable_set[-2:]
        ['b', 'a']

    IndexableSet implements the collections.Sequence interface.

    """
    def __init__(self, *args, **kwargs):
        super(IndexableSet, self).__init__(*args, key=hash, **kwargs)


class ItemSortedDict(SortedDict):
    """Sorted dictionary with key-function support for item pairs.

    Requires key function callable specified as the first argument. The
    callable must accept two arguments, key and value, and return a value used
    to determine the sort order. For example::

        def multiply(key, value):
            return key * value
        mapping = ItemSortedDict(multiply, [(3, 2), (4, 1), (2, 5)])
        list(mapping) == [4, 3, 2]

    Above, the key/value item pairs are ordered by ``key * value`` according to
    the callable given as the first argument.

    """
    def __init__(self, *args, **kwargs):
        assert len(args) > 0 and callable(args[0])
        args = list(args)
        func = self._func = args[0]
        def key_func(key):
            "Apply key function to (key, value) item pair."
            return func(key, self[key])
        args[0] = key_func
        super(ItemSortedDict, self).__init__(*args, **kwargs)

    def __delitem__(self, key):
        "``del mapping[key]``"
        if key not in self:
            raise KeyError(key)
        self._list_remove(key)
        self._delitem(key)

    def __setitem__(self, key, value):
        "``mapping[key] = value``"
        if key in self:
            self._list_remove(key)
            self._delitem(key)
        self._setitem(key, value)
        self._list_add(key)

    def copy(self):
        "Return shallow copy of the mapping."
        return self.__class__(self._func, self._load, self.iteritems())

    __copy__ = copy


class ValueSortedDict(SortedDict):
    """Sorted dictionary that maintains (key, value) item pairs sorted by value.

    - ``ValueSortedDict()`` -> new empty dictionary.

    - ``ValueSortedDict(mapping)`` -> new dictionary initialized from a mapping
      object's (key, value) pairs.

    - ``ValueSortedDict(iterable)`` -> new dictionary initialized as if via::

        d = ValueSortedDict()
        for k, v in iterable:
            d[k] = v

    - ``ValueSortedDict(**kwargs)`` -> new dictionary initialized with the
      name=value pairs in the keyword argument list.  For example::

        ValueSortedDict(one=1, two=2)

    An optional key function callable may be specified as the first
    argument. When so, the callable will be applied to the value of each item
    pair to determine the comparable for sort order as with Python's builtin
    ``sorted`` function.

    """
    def __init__(self, *args, **kwargs):
        args = list(args)
        if args and callable(args[0]):
            func = self._func = args[0]
            def key_func(key):
                "Apply key function to ``mapping[value]``."
                return func(self[key])
            args[0] = key_func
        else:
            self._func = None
            def key_func(key):
                "Return mapping value for key."
                return self[key]
            if args and args[0] is None:
                args[0] = key_func
            else:
                args.insert(0, key_func)
        super(ValueSortedDict, self).__init__(*args, **kwargs)

    def __delitem__(self, key):
        "``del mapping[key]``"
        if key not in self:
            raise KeyError(key)
        self._list_remove(key)
        self._delitem(key)

    def __setitem__(self, key, value):
        "``mapping[key] = value``"
        if key in self:
            self._list_remove(key)
            self._delitem(key)
        self._setitem(key, value)
        self._list_add(key)

    def copy(self):
        "Return shallow copy of the mapping."
        return self.__class__(self._func, self._load, self.iteritems())

    __copy__ = copy

    def __reduce__(self):
        items = [(key, self[key]) for key in self._list]
        args = (self._func, self._load, items)
        return (self.__class__, args)

    @recursive_repr
    def __repr__(self):
        temp = '{0}({1}, {2}, {{{3}}})'
        items = ', '.join('{0}: {1}'.format(repr(key), repr(self[key]))
                          for key in self._list)
        return temp.format(
            self.__class__.__name__,
            repr(self._func),
            repr(self._load),
            items
        )


class OrderedSet(co.MutableSet, co.Sequence):
    """Like OrderedDict, OrderedSet maintains the insertion order of elements.

    For example::

        >>> ordered_set = OrderedSet('abcde')
        >>> list(ordered_set) == list('abcde')
        >>> ordered_set = OrderedSet('edcba')
        >>> list(ordered_set) == list('edcba')

    OrderedSet also implements the collections.Sequence interface.

    """
    def __init__(self, iterable=()):
        self._keys = {}
        self._nums = SortedDict()
        self._count = count()
        self |= iterable

    def __contains__(self, key):
        "``key in ordered_set``"
        return key in self._keys

    count = __contains__

    def __iter__(self):
        "``iter(ordered_set)``"
        return self._nums.itervalues()

    def __reversed__(self):
        "``reversed(ordered_set)``"
        _nums = self._nums
        for key in reversed(_nums):
            yield _nums[key]

    def __getitem__(self, index):
        "``ordered_set[index]`` -> element; lookup element at index."
        _nums = self._nums
        num = _nums.iloc[index]
        return _nums[num]

    def __len__(self):
        "``len(ordered_set)``"
        return len(self._keys)

    def index(self, key):
        "Return index of key."
        try:
            return self._keys[key]
        except KeyError:
            raise ValueError('%r is not in %s' % (key, type(self).__name__))

    def add(self, key):
        "Add element, key, to set."
        if key not in self._keys:
            num = next(self._count)
            self._keys[key] = num
            self._nums[num] = key

    def discard(self, key):
        "Remove element, key, from set if it is a member."
        num = self._keys.pop(key, None)
        if num is not None:
            del self._nums[num]

    def __repr__(self):
        "Text representation of set."
        return '%s(%r)' % (type(self).__name__, list(self))

    __str__ = __repr__


class SegmentList(SortedListWithKey):
    """List that supports fast random insertion and deletion of elements.

    SegmentList is a special case of a SortedList initialized with a key
    function that always returns 0. As such, several SortedList methods are not
    implemented for SegmentList.

    """
    def __init__(self, iterable=()):
        super(SegmentList, self).__init__(iterable, self.zero)

    @staticmethod
    def zero(_):
        "Return 0."
        return 0

    def sort(self, key=None, reverse=False):
        "Stable sort in place."
        self[:] = sorted(self, key=key, reverse=reverse)

    def _not_implemented(self, *args, **kwargs):
        "Not implemented."
        raise NotImplementedError

    add = _not_implemented
    bisect = _not_implemented
    bisect_left = _not_implemented
    bisect_right = _not_implemented
    bisect_key = _not_implemented
    bisect_key_left = _not_implemented
    bisect_key_right = _not_implemented
    irange = _not_implemented
    update = _not_implemented
