import os
import os.path as op
import re

from pyrevit import PYREVIT_APP_DIR, PYREVIT_VERSION_APP_DIR, FIRST_LOAD
from pyrevit import PYREVIT_FILE_PREFIX_UNIVERSAL, PYREVIT_FILE_PREFIX, PYREVIT_FILE_PREFIX_STAMPED
from pyrevit.coreutils import make_canonical_name
from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
from System.IO import IOException


logger = get_logger(__name__)


TEMP_FILE_EXT = 'tmp'


def _remove_app_file(file_path):
    try:
        os.remove(file_path)
    except Exception as osremove_err:
        logger.error('Error file cleanup on: {} | {}'.format(file_path, osremove_err))


def _list_app_files(prefix, file_ext, universal=False):
    requested_files = []

    if universal:
        appdata_folder = PYREVIT_APP_DIR
    else:
        appdata_folder = PYREVIT_VERSION_APP_DIR

    for appdata_file in os.listdir(appdata_folder):
        if appdata_file.startswith(prefix) and appdata_file.endswith(file_ext):
            requested_files.append(op.join(appdata_folder, appdata_file))

    return requested_files


def _get_app_file(file_id, file_ext, filename_only=False, stamped=False, universal=False):
    appdata_folder = PYREVIT_VERSION_APP_DIR
    file_prefix = PYREVIT_FILE_PREFIX

    if stamped:
        file_prefix = PYREVIT_FILE_PREFIX_STAMPED
    elif universal:
        appdata_folder = PYREVIT_APP_DIR
        file_prefix = PYREVIT_FILE_PREFIX_UNIVERSAL

    full_filename = '{}_{}.{}'.format(file_prefix, file_id, file_ext)

    if filename_only:
        return full_filename
    else:
        return op.join(appdata_folder, full_filename)


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


def get_instance_data_file(file_id, file_ext=TEMP_FILE_EXT, name_only=False):
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


def is_file_available(file_name, file_ext, universal=False):
    if universal:
        full_filename = op.join(PYREVIT_APP_DIR, make_canonical_name(file_name, file_ext))
    else:
        full_filename = op.join(PYREVIT_VERSION_APP_DIR, make_canonical_name(file_name, file_ext))
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


def list_data_files(file_ext, universal=False):
    return _list_app_files(PYREVIT_FILE_PREFIX, file_ext, universal=universal)


def list_session_data_files(file_ext):
    return _list_app_files(PYREVIT_FILE_PREFIX_STAMPED, file_ext)


def garbage_data_file(file_path):
    _remove_app_file(file_path)


def cleanup_appdata_folder():
    if FIRST_LOAD:
        finder = re.compile('(.+)_(.+)_(.+)_(\d+).+')
        for appdata_file in os.listdir(PYREVIT_VERSION_APP_DIR):
            file_name_pieces = finder.findall(appdata_file)
            if file_name_pieces \
            and len(file_name_pieces[0]) == 4 \
            and int(file_name_pieces[0][3]) > 0 \
            and appdata_file.endswith(TEMP_FILE_EXT):
                _remove_app_file(op.join(PYREVIT_VERSION_APP_DIR, appdata_file))
