try:
    temp_name = __commandname__
    temp_path = __commandpath__
except:
    raise Exception('This is not a pyRevit script environment. These tools are irrelevant here.')

import os.path as op

from pyrevit import PyRevitException
from pyrevit.coreutils import get_all_subclasses
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.appdata import get_temp_file, get_session_data_file
from pyrevit.userconfig import user_config
from pyrevit.extensions.extensionmgr import get_command_from_path


scriptutils_logger = get_logger(__name__)

SCRIPT_CONFIG_POSTFIX = 'config'


def _make_script_file_id(file_id):
    return '{}_{}'.format(__commandname__, file_id)


def _get_script_info():
    # noinspection PyUnresolvedReferences
    return get_command_from_path(__commandpath__)


def _get_script_config():
    # noinspection PyUnresolvedReferences
    try:
        return getattr(user_config, __commandname__ + SCRIPT_CONFIG_POSTFIX)
    except:
        user_config.add_section(__commandname__ + SCRIPT_CONFIG_POSTFIX)
        return getattr(user_config, __commandname__ + SCRIPT_CONFIG_POSTFIX)


def _save_script_config():
    user_config.save_changes()


def _get_ui_button():
    # fixme: implement get_ui_button
    pass


# ----------------------------------------------------------------------------------------------------------------------
# Utilities available to scripts
# ----------------------------------------------------------------------------------------------------------------------

def get_script_temp_file(file_id):
    """Returns a filename to be used by a user script to store temporary information.
    Temporary files are saved in PYREVIT_APP_DIR and are cleaned up between Revit sessions.
    """
    return get_temp_file(_make_script_file_id(file_id))


def get_script_data_file(file_id, file_ext):
    """Returns a filename to be used by a user script to store temporary information.
    Temporary files are saved in PYREVIT_APP_DIR and are cleaned up between Revit sessions.
    """
    return get_session_data_file(_make_script_file_id(file_id), file_ext)


# noinspection PyUnresolvedReferences
logger = get_logger(__commandname__)
my_info = _get_script_info()
my_config = _get_script_config()
save_my_config = _save_script_config

my_temp_file = get_script_temp_file('defaulttemp')
my_data_file = get_script_data_file('defaultdata', 'data')
