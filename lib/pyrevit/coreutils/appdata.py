import os
import os.path as op

from pyrevit import PYREVIT_APP_DIR, PyRevitException
from pyrevit import PYREVIT_FILE_PREFIX_UNIVERSAL, PYREVIT_FILE_PREFIX, PYREVIT_FILE_PREFIX_STAMPED
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


def _get_app_file(file_id, file_ext, filename_only=False, stamped=False, universal=False):
    file_prefix = PYREVIT_FILE_PREFIX

    if stamped:
        file_prefix = PYREVIT_FILE_PREFIX_STAMPED
    elif universal:
        file_prefix = PYREVIT_FILE_PREFIX_UNIVERSAL

    full_filename = '{}_{}.{}'.format(file_prefix, file_id, file_ext)

    if filename_only:
        return full_filename
    else:
        return op.join(PYREVIT_APP_DIR, full_filename)


def get_universal_data_file(file_id, file_ext, name_only=False):
    """
    Get full file path to a file that is shared between all host versions
    These data files are not cleaned up at Revit restart.
    e.g pyrevit_eirannejad_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only and not the full file path

    Returns:
        str: File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext, filename_only=name_only, universal=True)


def get_data_file(file_id, file_ext, name_only=False):
    """
    Get full file path to a file that will not be cleaned up at Revit restart.
    e.g pyrevit_2016_eirannejad_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only and not the full file path

    Returns:
        str: File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext, filename_only=name_only)


def get_instance_data_file(file_id, file_ext, name_only=False):
    """
    Get full file path to a file that should be used by current host instance only.
    These data files will be cleaned up at Revit restart.
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
    return PYREVIT_FILE_PREFIX in file_name


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
    return _list_app_files(PYREVIT_FILE_PREFIX, file_ext)


def list_session_data_files(file_ext):
    return _list_app_files(PYREVIT_FILE_PREFIX_STAMPED, file_ext)


def cleanup_appdata_folder():
    pass


def garbage_data_file(file_path):
    _remove_app_file(file_path)
