"""Select the small engine-specific WPF boundary without loading legacy forms."""

from pyrevit.compat import IRONPY

if IRONPY:
    from .backends import _ipy as _impl
else:
    from .backends import _cpy as _impl

__all__ = [
    "Window",
    "Reactive",
    "list_source",
    "unwrap_item",
    "show_prompt",
    "bind_event",
    "bind_control_event",
    "dispose",
    "initialize",
    "items_source",
    "load_component",
    "unwrap",
    "validate_input",
]

if not IRONPY:
    __all__.extend(["Panel", "initialize_panel"])

globals().update((name, getattr(_impl, name)) for name in __all__)
