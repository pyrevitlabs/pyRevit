"""Actions behind the Copy State and Paste State buttons."""

# pylint: disable=import-error,invalid-name,attribute-defined-outside-init,
# pylint: disable=broad-except,missing-docstring
from pyrevit.coreutils import moduleutils

from copypastestate import basetypes
from copypastestate import actions


def get_actions():
    """Return the copy/paste action classes defined in `copypastestate.actions`."""
    return moduleutils.collect_marked(actions, basetypes.COPYPASTE_MARKER_PROPNAME)
