"""pyrevit.forms facade.

Both engines export the engine-neutral API defined in ``_common``. IronPython
adds its legacy names through ``_ipy``; CPython reports any other name as
unsupported.
"""

from pyrevit.compat import IRONPY

if IRONPY:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._ipy import *  # noqa: F401,F403
    from ._ipy import __all__  # noqa: F401
else:
    import importlib as _importlib

    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._common import *  # noqa: F401,F403
    from ._common import __all__  # noqa: F401
    from pyrevit import PyRevitCPythonNotSupported

    def __getattr__(name):
        if name == "settings_window":
            return _importlib.import_module("{}.{}".format(__name__, name))
        if name.startswith("_"):
            raise AttributeError(name)
        raise PyRevitCPythonNotSupported("pyrevit.forms.{}".format(name))
