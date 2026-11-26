"""Deprecated alias of the pre-split IronPython ``pyrevit.forms`` backend.

Re-exports the ``pyrevit.forms`` API and the private helpers extensions are
known to reach through this module, such as ``_WPFMixin``, so their imports
keep working after the split into feature modules.

Warning:
    Importing this module logs a deprecation message. Import from
    ``pyrevit.forms`` instead; this alias will be removed in a later release.

Note:
    This module must stay importable by IronPython 2.7.
"""

from pyrevit.coreutils.logger import get_logger
from pyrevit.forms import *  # noqa: F401,F403
from pyrevit.forms import __all__  # noqa: F401
from pyrevit.forms.base import _WPFMixin, _resolve_xaml_source  # noqa: F401
from pyrevit.forms.selection import (  # noqa: F401
    _get_preselect_names,
    _get_view_type_label,
    _make_param_def,
)
from pyrevit.forms._theme import (  # noqa: F401
    _BRAND_ACCENT,
    _BRAND_DARK,
    _BRAND_DARKER_DARK,
    _PALETTE_DARK,
    _PALETTE_LIGHT,
    _argb,
    _background_property,
    _colorref,
    _contrast_ratio,
    _foreground_property,
    _is_authored_value,
    _relative_luminance,
    _srgb_component,
    _walk_logical_tree,
)

get_logger(__name__).deprecate(
    "pyrevit.forms._ipy is deprecated; import from pyrevit.forms instead."
)
