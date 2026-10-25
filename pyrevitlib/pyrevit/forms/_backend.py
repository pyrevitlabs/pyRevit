"""Select the small engine-specific WPF boundary without loading legacy forms."""

from pyrevit.compat import IRONPY

if IRONPY:
    from .backends._ipy import (
        Window,
        bind_event,
        dispose,
        initialize,
        items_source,
        load_component,
        unwrap,
        validate_input,
    )
else:
    from .backends._cpy import (
        Window,
        bind_event,
        dispose,
        initialize,
        items_source,
        load_component,
        unwrap,
        validate_input,
    )

__all__ = [
    "Window",
    "bind_event",
    "dispose",
    "initialize",
    "items_source",
    "load_component",
    "unwrap",
    "validate_input",
]
