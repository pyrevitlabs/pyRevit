"""Select the small engine-specific WPF boundary without loading legacy forms."""

from pyrevit.compat import IRONPY

if IRONPY:
    from .backends._ipy import (
        Window,
        Reactive,
        list_source,
        unwrap_item,
        show_prompt,
        bind_event,
        bind_control_event,
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
        Reactive,
        list_source,
        unwrap_item,
        show_prompt,
        bind_event,
        bind_control_event,
        dispose,
        initialize,
        items_source,
        load_component,
        unwrap,
        validate_input,
    )

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
