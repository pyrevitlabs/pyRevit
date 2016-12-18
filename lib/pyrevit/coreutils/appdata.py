import os
import os.path as op

from pyrevit import USER_ROAMING_DIR, PYREVIT_ADDON_NAME, PYREVIT_APP_DIR, HOST_APP, PyRevitException
from pyrevit.coreutils import make_canonical_name
from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
from System.IO import IOException


logger = get_logger(__name__)


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


def _remove_app_file(file_path):
    try:
        os.remove(file_path)
    except Exception as osremove_err:
        logger.error('Error file cleanup on: {} | {}'.format(file_path, osremove_err))


def _list_app_files(prefix, file_ext):
    requested_files = []
    for appdata_file in os.listdir(PYREVIT_APP_DIR):
        if appdata_file.startswith(prefix) and appdata_file.endswith(file_ext):
            requested_files.append(op.join(PYREVIT_APP_DIR, appdata_file))

    return requested_files


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


def is_pyrevit_data_file(file_name):
    return APPDATA_FILE_PREFIX in file_name


def is_file_available(file_name, file_ext):
    full_filename = op.join(PYREVIT_APP_DIR, make_canonical_name(file_name, file_ext))
    if op.exists(full_filename):
        return full_filename
    else:
        return False


def is_data_file_available(file_id, file_ext):
    full_filename = _get_app_file(file_id, file_ext)
    if op.exists(full_filename):
        return full_filename
    else:
        return False


def list_data_files(file_ext):
    return _list_app_files(APPDATA_FILE_PREFIX, file_ext)


def list_session_data_files(file_ext):
    return _list_app_files(APPDATA_FILE_PREFIX_STAMPED, file_ext)


def cleanup_appdata_folder():
    for appdata_file in os.listdir(PYREVIT_APP_DIR):
        if appdata_file.startswith(APPDATA_TEMP_FILE_PREFIX):
            _remove_app_file(op.join(PYREVIT_APP_DIR, appdata_file))


def garbage_data_file(file_path):
    _remove_app_file(file_path)
