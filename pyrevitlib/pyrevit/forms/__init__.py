"""pyrevit.forms facade.

Both engines export the engine-neutral API defined in ``_common``. IronPython
adds its legacy names through ``_ipy``; CPython imports real submodules on
first access and reports any other public name as unsupported.
"""

from pyrevit.compat import IRONPY

if IRONPY:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._ipy import *  # noqa: F401,F403
    from ._ipy import __all__  # noqa: F401
else:
    import importlib as _importlib
    import importlib.util as _importlib_util

    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._common import *  # noqa: F401,F403
    from ._common import __all__  # noqa: F401
    from pyrevit import PyRevitCPythonNotSupported as _NotSupported

    class _UnsupportedName(_NotSupported, AttributeError):
        """A missing ``pyrevit.forms`` name that ``hasattr`` treats as absent."""

    def __getattr__(name):
        """Import a submodule on first access, or report the name as unsupported.

        Raises:
            AttributeError: ``name`` is private.
            PyRevitCPythonNotSupported: ``name`` is neither exported nor a
                submodule. The error is also an ``AttributeError``, so
                ``hasattr`` and ``getattr`` with a default treat it as absent,
                and ``from pyrevit.forms import name`` reports an ImportError.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        qualified = "{}.{}".format(__name__, name)
        if _importlib_util.find_spec(qualified) is not None:
            return _importlib.import_module(qualified)
        error = _UnsupportedName(qualified)
        error.name = name
        raise error
