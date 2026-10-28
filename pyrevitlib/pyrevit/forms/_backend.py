"""Select the small engine-specific WPF boundary without loading legacy forms.

Invariant:
    Both ``backends._ipy`` and ``backends._cpy`` define every name in
    ``__all__``; shared feature modules reach engine behavior only through
    these names and never compare native and Python objects themselves.

Note:
    ``list_source`` returns a managed ``IList`` snapshot on both engines:
    assign it to an ``ItemsSource`` and build a new one to change the list.
    ``items_of`` and the other ``*_of`` helpers return the original Python
    items on both engines: IronPython's live collections, or new Python
    lists under CPython. A caller that edits the ``items_of`` sequence in
    place calls ``rebind_if_changed`` afterwards so either engine shows it.
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
    "binding_source",
    "set_data_context",
    "list_source",
    "items_source",
    "items_of",
    "selected_items_of",
    "selected_item_of",
    "data_context_of",
    "rebind_if_changed",
    "initialize",
    "load_component",
    "queue_resource",
    "bind_event",
    "bind_control_event",
    "on_release",
    "show_prompt",
    "dispose",
    "disposing",
    "make_pane_provider",
    "unwrap",
]

globals().update((name, getattr(_impl, name)) for name in __all__)
