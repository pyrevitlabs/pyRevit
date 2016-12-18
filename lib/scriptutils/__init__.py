try:
    # noinspection PyUnresolvedReferences
    COMMAND_NAME = __commandname__
    # noinspection PyUnresolvedReferences
    COMMAND_PATH = __commandpath__
except:
    raise Exception('This is not a pyRevit script environment. These tools are irrelevant here.')

from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.appdata import get_temp_file, get_session_data_file
from pyrevit.userconfig import user_config
from pyrevit.extensions.extensionmgr import get_command_from_path


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
    """Returns a filename to be used by a user script to store data.
    Data files are saved in PYREVIT_APP_DIR and are NOT cleaned up between Revit sessions.
    """
    return get_session_data_file(_make_script_file_id(file_id), file_ext)


logger = get_logger(COMMAND_NAME)
my_info = _get_script_info()
my_config = _get_script_config()
save_my_config = _save_script_config

my_temp_file = get_script_temp_file('defaulttemp')
my_data_file = get_script_data_file('defaultdata', 'data')
