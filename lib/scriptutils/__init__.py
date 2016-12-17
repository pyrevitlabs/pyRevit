import os.path as op

from pyrevit import PyRevitException
from pyrevit.coreutils import get_all_subclasses

from pyrevit.coreutils.logger import get_logger
from pyrevit.extensions.extensionmgr import get_command_from_path


scriptutils_logger = get_logger(__name__)


def _get_script_info():
    # noinspection PyUnresolvedReferences
    return get_command_from_path(__commandpath__)


def _get_ui_button():
    # fixme: implement get_ui_button
    pass


def _get_temp_file():
    """Returns a filename to be used by a user script to store temporary information.
    Temporary files are saved in PYREVIT_APP_DIR.
    """
    # fixme temporary file
    pass


# ----------------------------------------------------------------------------------------------------------------------
# Utilities available to scripts
# ----------------------------------------------------------------------------------------------------------------------

# noinspection PyUnresolvedReferences
logger = get_logger(__commandname__)
my_info = _get_script_info()
