try:
    # noinspection PyUnresolvedReferences
    COMMAND_NAME = __commandname__
    # noinspection PyUnresolvedReferences
    COMMAND_PATH = __commandpath__
except:
    raise Exception('This is not a pyRevit script environment. These tools are irrelevant here.')

import webbrowser

# noinspection PyUnresolvedReferences
from pyrevit import PyRevitException
# noinspection PyUnresolvedReferences
from pyrevit.versionmgr import PYREVIT_VERSION
# noinspection PyUnresolvedReferences
import pyrevit.coreutils as coreutils

from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.appdata import get_session_data_file
from pyrevit.coreutils.console import output_window
from pyrevit.userconfig import user_config
from pyrevit.extensions.extensionmgr import get_command_from_path

from scriptutils import journals
from pyrevit.coreutils import ipyengine


scriptutils_logger = get_logger(__name__)


SCRIPT_CONFIG_POSTFIX = 'config'


def _make_script_file_id(file_id):
    return '{}_{}'.format(COMMAND_NAME, file_id)


def _get_script_info():
    return get_command_from_path(COMMAND_PATH)


def _get_script_config():
    try:
        return getattr(user_config, COMMAND_NAME + SCRIPT_CONFIG_POSTFIX)
    except:
        user_config.add_section(COMMAND_NAME + SCRIPT_CONFIG_POSTFIX)
        return getattr(user_config, COMMAND_NAME + SCRIPT_CONFIG_POSTFIX)


def _save_script_config():
    user_config.save_changes()


def _get_ui_button():
    # fixme: implement get_ui_button
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# Utilities available to scripts
# ----------------------------------------------------------------------------------------------------------------------

def open_url(url):
    """Opens url in a new tab in the default web browser."""
    return webbrowser.open_new_tab(url)


def get_script_data_file(file_id, file_ext):
    """Returns a filename to be used by a user script to store data.
    Data files are saved in PYREVIT_APP_DIR and are NOT cleaned up between Revit sessions.
    """
    return get_session_data_file(_make_script_file_id(file_id), file_ext)


logger = get_logger(COMMAND_NAME)

my_info = _get_script_info()

my_config = _get_script_config()
save_my_config = _save_script_config

my_button = _get_ui_button()

my_data_file = get_script_data_file('defaultdata', 'data')
my_journal = journals

my_output = output_window

try:
    my_engine = ipyengine.get_engine_wrapper()
except:
    scriptutils_logger.debug('__engine__ not found at script runtime: {}'.format(my_info))
