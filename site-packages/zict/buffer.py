from itertools import chain

from .common import ZictBase, close
from .lru import LRU


class Buffer(ZictBase):
    """ Buffer one dictionary on top of another

    This creates a MutableMapping by combining two MutableMappings, one that
    feeds into the other when it overflows, based on an LRU mechanism.  When
    the first evicts elements these get placed into the second.  When an item
    is retrieved from the second it is placed back into the first.

    Parameters
    ----------
    fast: MutableMapping
    slow: MutableMapping
    fast_to_slow_callbacks: list of callables
        These functions run every time data moves from the fast to the slow
        mapping.  They take two arguments, a key and a value
    slow_to_fast_callbacks: list of callables
        These functions run every time data moves form the slow to the fast
        mapping.

    Examples
    --------
    >>> fast = dict()
    >>> slow = Func(dumps, loads, File('storage/'))  # doctest: +SKIP
    >>> def weight(k, v):
    ...     return sys.getsizeof(v)
    >>> buff = Buffer(fast, slow, 1e8, weight=weight)  # doctest: +SKIP

    See Also
    --------
    LRU
    """
    def __init__(self, fast, slow, n, weight=lambda k, v: 1,
                 fast_to_slow_callbacks=None, slow_to_fast_callbacks=None):
        self.fast = LRU(n, fast, weight=weight, on_evict=[self.fast_to_slow])
        self.slow = slow
        self.n = n
        self.weight = weight
        if callable(fast_to_slow_callbacks):
            fast_to_slow_callbacks = [fast_to_slow_callbacks]
        if callable(slow_to_fast_callbacks):
            slow_to_fast_callbacks = [slow_to_fast_callbacks]
        self.fast_to_slow_callbacks = fast_to_slow_callbacks or []
        self.slow_to_fast_callbacks = slow_to_fast_callbacks or []

    def fast_to_slow(self, key, value):
        self.slow[key] = value
        for cb in self.fast_to_slow_callbacks:
            cb(key, value)

    def slow_to_fast(self, key):
        value = self.slow[key]
        # Avoid useless movement for heavy values
        if self.weight(key, value) <= self.n:
            del self.slow[key]
            self.fast[key] = value
        for cb in self.slow_to_fast_callbacks:
            cb(key, value)
        return value

    def __getitem__(self, key):
        if key in self.fast:
            return self.fast[key]
        elif key in self.slow:
            return self.slow_to_fast(key)
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        weight = self.weight(key, value)
        # Avoid useless movement for heavy values
        if self.weight(key, value) <= self.n:
            if key in self.slow:
                del self.slow[key]
            self.fast[key] = value
        else:
            self.slow[key] = value

    def __delitem__(self, key):
        if key in self.fast:
            del self.fast[key]
        elif key in self.slow:
            del self.slow[key]
        else:
            raise KeyError(key)

    def keys(self):
        return chain(self.fast.keys(), self.slow.keys())

    def values(self):
        return chain(self.fast.values(), self.slow.values())

    def items(self):
        return chain(self.fast.items(), self.slow.items())

    def __len__(self):
        return len(self.fast) + len(self.slow)

    def __iter__(self):
        return chain(iter(self.fast), iter(self.slow))

    def __contains__(self, key):
        return key in self.fast or key in self.slow

    def __str__(self):
        return 'Buffer<%s, %s>' % (str(self.fast), str(self.slow))

    __repr__ = __str__

    def flush(self):
        self.fast.flush()
        self.slow.flush()

    def close(self):
        close(self.fast)
        close(self.slow)
