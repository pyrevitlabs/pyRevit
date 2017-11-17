from __future__ import absolute_import, division, print_function

from heapdict import heapdict

from .common import ZictBase, close


def do_nothing(k, v):
    pass


class LRU(ZictBase):
    """ Evict Least Recently Used Elements

    Parameters
    ----------
    n: int
        Number of elements to keep, or total weight if weight= is used
    d: MutableMapping
        Dictionary in which to hold elements
    on_evict: list of callables
        Function:: k, v -> action to call on key value pairs prior to eviction
    weight: callable
        Function:: k, v -> number to determine the size of keeping the item in
        the mapping.  Defaults to ``(k, v) -> 1``

    Examples
    --------
    >>> lru = LRU(2, dict(), on_evict=lambda k, v: print("Lost", k, v))
    >>> lru['x'] = 1
    >>> lru['y'] = 2
    >>> lru['z'] = 3
    Lost x 1
    """
    def __init__(self, n, d, on_evict=None, weight=lambda k, v: 1):
        self.d = d
        self.n = n
        self.heap = heapdict()
        self.i = 0
        if callable(on_evict):
            on_evict = [on_evict]
        self.on_evict = on_evict or []
        self.weight = weight
        self.total_weight = 0
        self.weights = dict()

    def __getitem__(self, key):
        result = self.d[key]
        self.i += 1
        self.heap[key] = self.i
        return result

    def __setitem__(self, key, value):
        if key in self.d:
            del self[key]

        weight = self.weight(key, value)

        if weight <= self.n:
            self.d[key] = value
            self.i += 1
            self.heap[key] = self.i

            self.weights[key] = weight
            self.total_weight += weight
        else:
            for cb in self.on_evict:
                cb(key, value)

        while self.total_weight > self.n:
            self.evict()

    def evict(self):
        """ Evict least recently used key

        This is typically called from internal use, but can be externally
        triggered as well.

        Returns
        -------
        k: key
        v: value
        w: weight
        """
        k, priority = self.heap.popitem()
        weight = self.weights.pop(k)
        self.total_weight -= weight
        v = self.d.pop(k)
        for cb in self.on_evict:
            cb(k, v)
        return k, v, weight

    def __delitem__(self, key):
        del self.d[key]
        del self.heap[key]
        self.total_weight -= self.weights.pop(key)

    def keys(self):
        return self.d.keys()

    def values(self):
        return self.d.values()

    def items(self):
        return self.d.items()

    def __len__(self):
        return len(self.d)

    def __iter__(self):
        return iter(self.d)

    def __contains__(self, key):
        return key in self.d

    def __str__(self):
        sub = str(self.d) if not isinstance(self.d, dict) else 'dict'
        return '<LRU: %s/%s on %s>' % (self.total_weight, self.n, sub)

    __repr__ = __str__

    def flush(self):
        self.d.flush()

    def close(self):
        close(self.d)
