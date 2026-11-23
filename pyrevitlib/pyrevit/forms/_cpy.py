"""Deprecated alias of the pre-split CPython ``pyrevit.forms`` backend.

The CPython backend now provides the real forms, so this module re-exports
the ``pyrevit.forms`` API for extensions that imported it directly.

Warning:
    Importing this module logs a deprecation message. Import from
    ``pyrevit.forms`` instead; this alias will be removed in a later release.
"""

from pyrevit.coreutils.logger import get_logger
from pyrevit.forms import *  # noqa: F401,F403
from pyrevit.forms import __all__  # noqa: F401

get_logger(__name__).deprecate(
    "pyrevit.forms._cpy is deprecated; import from pyrevit.forms instead."
)
