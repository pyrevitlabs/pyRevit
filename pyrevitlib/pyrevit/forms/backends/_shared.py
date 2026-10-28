"""Engine-neutral helpers that both WPF backends build their contract from.

Note:
    This module must stay importable by IronPython 2.7 and must not import
    WPF or Revit types, so the portable tests can load it directly.
"""


class Disposing(object):
    """Dispose a form whose construction raised, then let the error propagate.

    Args:
        target (object): The form under construction.
        dispose (callable): The backend's ``dispose(target)``.
    """

    def __init__(self, target, dispose):
        self._target = target
        self._dispose = dispose

    def __enter__(self):
        return self._target

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and issubclass(exc_type, Exception):
            self._dispose(self._target)
        return False


def same_items(first, second):
    """Return whether two sequences list the same objects in the same order."""
    first = list(first)
    second = list(second)
    return len(first) == len(second) and all(
        left is right for left, right in zip(first, second)
    )


def apply_pane_options(panel, target):
    """Copy a panel's optional Revit pane settings that are set onto ``target``.

    ``target`` is the pane setup data under IronPython and the managed pane
    provider under CPython; both expose the same three properties.
    """
    if panel.initial_state is not None:
        target.InitialState = panel.initial_state
    if panel.editor_interaction is not None:
        target.EditorInteraction = panel.editor_interaction
    if panel.contextual_help is not None:
        target.ContextualHelp = panel.contextual_help
