"""Selection helpers and IronPython-only RPW forms.

Note:
    FlexForm mixes Python and CLR base classes, which Python.NET cannot load.
    CPython can import RPW's host and selection helpers without loading forms.
"""

import platform

if platform.python_implementation() == "IronPython":
    from rpw.ui import forms


def __getattr__(name):
    if name == "forms":
        raise NotImplementedError(
            "RPW forms require IronPython"
        )
    raise AttributeError("module 'rpw.ui' has no attribute '{}'".format(name))


from rpw.ui.selection import Selection, Pick
