"""Select the small engine-specific WPF boundary without loading legacy forms.

Invariant:
    Both ``backends._ipy`` and ``backends._cpy`` define every name in
    ``__all__``; shared feature modules reach engine behavior only through
    these names.
"""

from pyrevit.compat import IRONPY

if IRONPY:
    from .backends import _ipy as _impl
else:
    from .backends import _cpy as _impl

__all__ = [
    "Window",
    "Panel",
    "Reactive",
    "list_source",
    "unwrap_item",
    "show_prompt",
    "bind_event",
    "bind_control_event",
    "dispose",
    "initialize",
    "initialize_panel",
    "items_source",
    "load_component",
    "make_pane_provider",
    "activate_open_window",
    "unwrap",
    "validate_input",
]

globals().update((name, getattr(_impl, name)) for name in __all__)
