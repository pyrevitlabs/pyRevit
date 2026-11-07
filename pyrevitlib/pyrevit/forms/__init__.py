"""pyrevit.forms facade.

Both engines export the engine-neutral API defined in ``_common``. IronPython
adds its legacy names through ``_ipy_legacy``; CPython imports real submodules
on first access and reports any other public name as unsupported.
"""

from pyrevit.compat import IRONPY

if IRONPY:
    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._ipy_legacy import *  # noqa: F401,F403
    from ._ipy_legacy import __all__  # noqa: F401
else:
    import importlib as _importlib
    import importlib.util as _importlib_util

    # pylint: disable=wildcard-import,unused-wildcard-import
    from ._common import *  # noqa: F401,F403
    from ._common import __all__  # noqa: F401
    from ._legacy_exports import LEGACY_EXPORTS as _LEGACY_EXPORTS
    from pyrevit import PyRevitCPythonNotSupported as _NotSupported

    _UNPORTED_NAMES = frozenset(_LEGACY_EXPORTS) - frozenset(__all__)
    _submodule_specs = {}

    class _UnsupportedName(_NotSupported, AttributeError):
        """A missing ``pyrevit.forms`` name that ``hasattr`` treats as absent."""

    def _unsupported_name(name):
        error = _UnsupportedName("{}.{}".format(__name__, name))
        error.name = name
        return error

    def _is_submodule(qualified):
        if qualified not in _submodule_specs:
            _submodule_specs[qualified] = (
                _importlib_util.find_spec(qualified) is not None
            )
        return _submodule_specs[qualified]

    def __getattr__(name):
        """Import a submodule on first access, or report the name as unsupported.

        Submodule lookups are cached, so repeated misses do not search the
        package again.

        Raises:
            AttributeError: ``name`` is private.
            PyRevitCPythonNotSupported: ``name`` is a legacy IronPython export
                that CPython does not provide. The error is deliberately not an
                ``AttributeError``, so ``from pyrevit.forms import name``
                reports the unsupported feature instead of a generic
                ``ImportError``.
            _UnsupportedName: ``name`` is unknown, or names a submodule that
                failed to import (chained as ``__cause__``). It is both a
                ``PyRevitCPythonNotSupported`` and an ``AttributeError``, so
                ``hasattr`` and ``getattr`` with a default treat it as absent.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        qualified = "{}.{}".format(__name__, name)
        if _is_submodule(qualified):
            try:
                return _importlib.import_module(qualified)
            except ImportError as import_error:
                error = _unsupported_name(name)
                error.__cause__ = import_error
                raise error
        if name in _UNPORTED_NAMES:
            raise _NotSupported(qualified)
        raise _unsupported_name(name)
