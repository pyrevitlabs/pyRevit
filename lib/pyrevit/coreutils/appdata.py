import os
import os.path as op

from pyrevit import USER_ROAMING_DIR, PYREVIT_ADDON_NAME, HOST_APP
from pyrevit.core.exceptions import PyRevitException

# noinspection PyUnresolvedReferences
from System.IO import IOException


# pyrevit temp file directory
PYREVIT_APP_DIR = op.join(USER_ROAMING_DIR, 'pyRevit')

if not op.isdir(PYREVIT_APP_DIR):
    try:
        os.mkdir(PYREVIT_APP_DIR)
    except (OSError, IOException) as err:
        raise PyRevitException('Can not access pyRevit folder at: {} | {}'.format(PYREVIT_APP_DIR, err))


APPDATA_FILE_PREFIX = '{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                        HOST_APP.version, HOST_APP.username)
APPDATA_FILE_PREFIX_STAMPED = '{}_{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                   HOST_APP.version, HOST_APP.username, HOST_APP.proc_id)
APPDATA_TEMP_FILE_PREFIX = 'TEMP_'


def _get_app_file(file_id, file_ext, filename_only=False, temp_file=False, stamped=False):
    file_prefix = APPDATA_FILE_PREFIX
    if stamped:
        file_prefix = APPDATA_FILE_PREFIX_STAMPED

    full_filename = '{}_{}.{}'.format(file_prefix, file_id, file_ext)

    if temp_file:
        full_filename = APPDATA_TEMP_FILE_PREFIX + full_filename

    if filename_only:
        return full_filename
    else:
        return op.join(PYREVIT_APP_DIR, full_filename)


def _get_stamped_base_file(file_id, file_ext):
    return '{}_{}.{}'.format(APPDATA_FILE_PREFIX_STAMPED, file_id, file_ext)


def get_temp_file(file_id, file_ext='tmp', name_only=False):
    """
    Get full file path to a file that is temporary and will be cleaned up between sessions.
    e.g TEMP_pyrevit_2016_eirannejad_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only and not the full file path

    Returns:
        str: File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext, temp_file=True, filename_only=name_only)


def get_data_file(file_id, file_ext, name_only=False):
    """
    Get full file path to a file that will not be cleaned up between sessions.
    e.g pyrevit_2016_eirannejad_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only and not the full file path

    Returns:
        str: File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext, filename_only=name_only)


def get_session_data_file(file_id, file_ext, name_only=False):
    """
    Get full file path to a file that should be used by current host instance only.
    e.g pyrevit_2016_eirannejad_2353_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only and not the full file path

    Returns:
        str: File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext, filename_only=name_only, stamped=True)


def is_data_file_available(file_id, file_ext):
    full_filename = _get_app_file(file_id, file_ext)
    return op.exists(full_filename)
