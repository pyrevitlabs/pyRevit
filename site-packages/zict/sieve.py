from __future__ import absolute_import, division, print_function

from collections import defaultdict
from itertools import chain
import sys

from .common import ZictBase, close


class Sieve(ZictBase):
    """ Store values in different mappings based on a selector's
    output.

    This creates a MutableMapping combining several underlying
    MutableMappings for storage.  Items are dispatched based on
    a selector function provided by the user.

    Parameters
    ----------
    mappings: dict of {mapping key: MutableMapping}
    selector: callable (key, value) -> mapping key

    Examples
    --------
    >>> small = {}
    >>> large = DataBase()                        # doctest: +SKIP
    >>> mappings = {True: small, False: large}    # doctest: +SKIP
    >>> def is_small(key, value):                 # doctest: +SKIP
            return sys.getsizeof(value) < 10000
    >>> d = Sieve(mappings, is_small)             # doctest: +SKIP

    See Also
    --------
    Buffer
    """
    def __init__(self, mappings, selector):
        self.mappings = mappings
        self.selector = selector
        self.key_to_mapping = {}

    def __getitem__(self, key):
        return self.key_to_mapping[key][key]

    def __setitem__(self, key, value):
        old_mapping = self.key_to_mapping.get(key)
        mapping = self.mappings[self.selector(key, value)]
        if old_mapping is not None and old_mapping is not mapping:
            del old_mapping[key]
        mapping[key] = value
        self.key_to_mapping[key] = mapping

    def __delitem__(self, key):
        del self.key_to_mapping.pop(key)[key]

    def _do_update(self, items):
        # Optimized update() implementation issuing a single update()
        # call per underlying mapping.
        to_delete = []
        updates = defaultdict(list)
        mapping_ids = dict((id(m), m) for m in self.mappings.values())

        for key, value in items:
            old_mapping = self.key_to_mapping.get(key)
            mapping = self.mappings[self.selector(key, value)]
            if old_mapping is not None and old_mapping is not mapping:
                del old_mapping[key]
            # Can't hash a mutable mapping, so use its id() instead
            updates[id(mapping)].append((key, value))

        for mid, mitems in updates.items():
            mapping = mapping_ids[mid]
            mapping.update(mitems)
            for key, _ in mitems:
                self.key_to_mapping[key] = mapping

    def keys(self):
        return chain.from_iterable(self.mappings.values())

    def values(self):
        return chain.from_iterable(m.values() for m in self.mappings.values())

    def items(self):
        return chain.from_iterable(m.items() for m in self.mappings.values())

    def __len__(self):
        return sum(map(len, self.mappings.values()))

    __iter__ = keys

    def __contains__(self, key):
        return key in self.key_to_mapping

    def __str__(self):
        return 'Sieve<%s>' % (str(self.mappings),)

    __repr__ = __str__

    def flush(self):
        for m in self.mappings.values():
            m.flush()

    def close(self):
        for m in self.mappings.values():
            close(m)
