"""pyrevit.forms facade.

Imports the engine-specific forms backend for the active Python engine.
"""

from pyrevit.compat import IRONPY

if IRONPY:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._ipy import *  # noqa: F401,F403
else:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._cpy import *  # noqa: F401,F403
    from . import _cpy as _backend
    from pyrevit import PyRevitCPythonNotSupported

    __all__ = list(getattr(_backend, "__all__", []))

    def __getattr__(name):
        raise PyRevitCPythonNotSupported("pyrevit.forms.{}".format(name))
