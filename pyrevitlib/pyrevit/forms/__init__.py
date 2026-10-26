"""pyrevit.forms facade.

Imports the engine-specific forms backend for the active Python engine.
"""

from pyrevit.compat import IRONPY

if IRONPY:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._ipy import *  # noqa: F401,F403
else:
    import importlib as _importlib

    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._cpy import *  # noqa: F401,F403
    from . import _cpy as _cpy_exports
    from pyrevit import PyRevitCPythonNotSupported

    __all__ = list(getattr(_cpy_exports, "__all__", []))

    def __getattr__(name):
        if name == "settings_window":
            return _importlib.import_module("{}.{}".format(__name__, name))
        if name.startswith("_"):
            raise AttributeError(name)
        raise PyRevitCPythonNotSupported("pyrevit.forms.{}".format(name))
