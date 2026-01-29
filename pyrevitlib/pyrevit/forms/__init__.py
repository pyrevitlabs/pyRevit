"""pyrevit.forms facade.

Routes to the IronPython backend (`_ipy_forms`) when `pyrevit.compat.IRONPY`
is true. Under CPython, imports succeed by routing to `_cpy_forms` and
unsupported symbols raise `PyRevitCPythonNotSupported("pyrevit.forms.<symbol>")`.
"""

from pyrevit.compat import IRONPY

if IRONPY:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._ipy_forms import *  # noqa: F401,F403
else:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._cpy_forms import *  # noqa: F401,F403
    from . import _cpy_forms as _backend
    from pyrevit import PyRevitCPythonNotSupported as _PyRevitCPythonNotSupported

    __all__ = list(getattr(_backend, "__all__", []))

    def __getattr__(name):
        raise _PyRevitCPythonNotSupported("pyrevit.forms.{}".format(name))
