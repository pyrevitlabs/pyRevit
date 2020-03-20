# pylint: disable=import-error,invalid-name,attribute-defined-outside-init,
# pylint: disable=broad-except,missing-docstring
from pyrevit.coreutils import logger
from pyrevit.coreutils import moduleutils

from copypastestate import utils
from copypastestate import basetypes
from copypastestate import actions


mlogger = logger.get_logger(__name__)


def get_actions():
    return moduleutils.collect_marked(
        actions,
        basetypes.COPYPASTE_MARKER_PROPNAME
        )
