from __future__ import absolute_import, division, print_function

from collections import Mapping, MutableMapping


class ZictBase(MutableMapping):
    """
    Base class for zict mappings.
    """

    def update(*args, **kwds):
        # Boilerplate for implementing an update() method
        if not args:
            raise TypeError("descriptor 'update' of MutableMapping object "
                            "needs an argument")
        self = args[0]
        args = args[1:]
        if len(args) > 1:
            raise TypeError('update expected at most 1 arguments, got %d' %
                            len(args))
        items = []
        if args:
            other = args[0]
            if isinstance(other, Mapping) or hasattr(other, "items"):
                items += other.items()
            else:
                # Assuming (key, value) pairs
                items += other
        if kwds:
            items += kwds.items()
        self._do_update(items)

    def _do_update(self, items):
        # Default implementation, can be overriden for speed
        for k, v in items:
            self[k] = v

    def close(self):
        """
        Release any system resources held by this object.
        """

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def close(z):
    """
    Close *z* if possible.
    """
    if hasattr(z, "close"):
        z.close()
