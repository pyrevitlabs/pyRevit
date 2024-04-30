"""Utility functions for creating data files within pyRevit environment.

Most times, scripts need to save some data to share between different scripts
that work on a similar topic or between script executions. This module provides
the necessary and consistent mechanism for creating and maintaining such files.

Examples:
    ```python
    from pyrevit.coreutils import appdata
    appdata.list_data_files()
    ```
"""

import os
import os.path as op
import re

import pyrevit
from pyrevit import EXEC_PARAMS
from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit.labs import TargetApps


#pylint: disable=W0703,C0302
mlogger = logger.get_logger(__name__)  #pylint: disable=C0103


TEMP_FILE_EXT = 'tmp'


def _remove_app_file(file_path):
    try:
        os.remove(file_path)
    except Exception as osremove_err:
        mlogger.debug('Error file cleanup on: %s | %s', file_path, osremove_err)


def _list_app_folders():
    app_folders = []
    for appdata_entry in os.listdir(pyrevit.PYREVIT_APP_DIR):
        if re.match(pattern=r'^\d{4}$', string=appdata_entry):
            app_folder = op.join(pyrevit.PYREVIT_APP_DIR, appdata_entry)
            if op.isdir(app_folder):
                app_folders.append(app_folder)
    return app_folders


def _list_app_files(prefix, file_ext, universal=False):
    requested_files = []

    if universal:
        appdata_folder = pyrevit.PYREVIT_APP_DIR
    else:
        appdata_folder = pyrevit.PYREVIT_VERSION_APP_DIR

    for appdata_file in os.listdir(appdata_folder):
        if appdata_file.startswith(prefix) and appdata_file.endswith(file_ext):
            requested_files.append(op.join(appdata_folder, appdata_file))

    return requested_files


def _get_app_file(file_id, file_ext,
                  filename_only=False, stamped=False, universal=False):
    appdata_folder = pyrevit.PYREVIT_VERSION_APP_DIR
    file_prefix = pyrevit.PYREVIT_FILE_PREFIX

    if stamped:
        file_prefix = pyrevit.PYREVIT_FILE_PREFIX_STAMPED
    elif universal:
        appdata_folder = pyrevit.PYREVIT_APP_DIR
        file_prefix = pyrevit.PYREVIT_FILE_PREFIX_UNIVERSAL

    full_filename = '{}{}.{}'.format(file_prefix, file_id, file_ext)

    if filename_only:
        return full_filename
    else:
        return op.join(
            appdata_folder,
            coreutils.cleanup_filename(full_filename)
            )


def _match_file(file_name):
    match = re.match(pattern=pyrevit.PYREVIT_FILE_PREFIX_STAMPED_USER_REGEX,
                     string=file_name)
    if match:
        return match.groupdict()

    # e.g. pyRevit_2018_14422_
    match = re.match(pattern=pyrevit.PYREVIT_FILE_PREFIX_STAMPED_REGEX,
                     string=file_name)
    if match:
        return match.groupdict()

    # e.g. pyRevit_2018_pyrevitlabs_
    match = re.match(pattern=pyrevit.PYREVIT_FILE_PREFIX_USER_REGEX,
                     string=file_name)
    if match:
        return match.groupdict()

    # e.g. pyRevit_2018_
    match = re.match(pattern=pyrevit.PYREVIT_FILE_PREFIX_REGEX,
                     string=file_name)
    if match:
        return match.groupdict()

    # e.g. pyRevit_pyrevitlabs_
    match = re.match(pattern=pyrevit.PYREVIT_FILE_PREFIX_UNIVERSAL_USER_REGEX,
                     string=file_name)
    if match:
        return match.groupdict()

    # e.g. pyRevit_
    match = re.match(pattern=pyrevit.PYREVIT_FILE_PREFIX_UNIVERSAL_REGEX,
                     string=file_name)
    if match:
        return match.groupdict()

    return {}


def get_universal_data_file(file_id, file_ext, name_only=False):
    """Get path to file that is shared between all host versions.

    These data files are not cleaned up at Revit restart.
    e.g pyrevit_pyrevitlabs_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only

    Returns:
        (str): File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext,
                         filename_only=name_only, universal=True)


def get_data_file(file_id, file_ext, name_only=False):
    """Get path to file that will not be cleaned up at Revit load.

    e.g pyrevit_2016_pyrevitlabs_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only

    Returns:
        (str): File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext, filename_only=name_only)


def get_instance_data_file(file_id, file_ext=TEMP_FILE_EXT, name_only=False):
    """Get path to file that should be used by current instance only.

    These data files will be cleaned up at Revit restart.
    e.g pyrevit_2016_pyrevitlabs_2353_file_id.file_ext

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension
        name_only (bool): If true, function returns file name only

    Returns:
        (str): File name or full file path (depending on name_only)
    """
    return _get_app_file(file_id, file_ext,
                         filename_only=name_only, stamped=True)


def is_pyrevit_data_file(file_name):
    """Check if given file is a pyRevit data file.

    Args:
        file_name (str): file name

    Returns:
        (bool): True if file is a pyRevit data file
    """
    return pyrevit.PYREVIT_FILE_PREFIX in file_name


def is_file_available(file_name, file_ext, universal=False):
    """Check if given file is available within appdata directory.

    Args:
        file_name (str): file name
        file_ext (str): file extension
        universal (bool): Check against universal data files

    Returns:
        (str | bool): file path if file is available
    """
    if universal:
        full_filename = op.join(
            pyrevit.PYREVIT_APP_DIR,
            coreutils.make_canonical_name(file_name, file_ext))
    else:
        full_filename = op.join(
            pyrevit.PYREVIT_VERSION_APP_DIR,
            coreutils.make_canonical_name(file_name, file_ext))
    if op.exists(full_filename):
        return full_filename
    else:
        return False


def is_data_file_available(file_id, file_ext):
    """Check if given file is available within appdata directory.

    Args:
        file_id (str): data file id
        file_ext (str): file extension

    Returns:
        (str): file path if file is available
    """
    full_filename = _get_app_file(file_id, file_ext)
    if op.exists(full_filename):
        return full_filename
    else:
        return False


def list_data_files(file_ext, universal=False):
    """List all data files with given extension.

    Args:
        file_ext (str): file extension
        universal (bool): Check against universal data files

    Returns:
        (list[str]): list of files
    """
    return _list_app_files(
        pyrevit.PYREVIT_FILE_PREFIX,
        file_ext,
        universal=universal
        )


def list_instance_data_files(file_ext):
    """List all data files associated with current session.

    Args:
        file_ext (str): data files with this extension will be listed only.

    Returns:
        (list[str]): list of data files

    """
    return _list_app_files(pyrevit.PYREVIT_FILE_PREFIX_STAMPED, file_ext)


def find_data_files(file_ext):
    """Find data files in all data files directories.

    Args:
        file_ext (str): data files with this extension will be listed only

    Returns:
        (list[str]): list of files
    """
    all_datafiles = set()
    for app_folder in _list_app_folders():
        for appdata_file in os.listdir(app_folder):
            file_naming_dict = _match_file(
                op.basename(appdata_file)
            )
            if file_naming_dict \
                    and file_naming_dict['fname'].endswith(file_ext):
                all_datafiles.add(
                    op.join(app_folder, appdata_file)
                    )
    return all_datafiles


def find_instance_data_files(file_ext, instance_id):
    """Find instance data files in all data files directories.

    Args:
        file_ext (str): data files with this extension will be listed only
        instance_id (int): list data files for this instance id only

    Returns:
        (list[str]): list of files
    """
    # instance files names are like pyRevit_2018_14422_
    instance_files = set()
    for appdata_file in find_data_files(file_ext):
        file_naming_dict = _match_file(
            op.basename(appdata_file)
        )
        if 'pid' in file_naming_dict:
            try:
                pid = int(file_naming_dict['pid'])
                if instance_id == pid:
                    instance_files.add(appdata_file)
            except Exception:
                pass
    return instance_files


def garbage_data_file(file_path):
    """Mark and remove the given appdata file.

    Current implementation removes the file immediately.

    Args:
        file_path (str): path to the target file
    """
    _remove_app_file(file_path)


def cleanup_appdata_folder():
    """Cleanup appdata folder of all temporary appdata files."""
    if EXEC_PARAMS.first_load:
        hostapp_pids = \
            [x.ProcessId
             for x in TargetApps.Revit.RevitController.ListRunningRevits()]
        for appdata_file in os.listdir(pyrevit.PYREVIT_VERSION_APP_DIR):
            file_naming_dict = _match_file(appdata_file)
            if 'pid' in file_naming_dict:
                try:
                    pid = int(file_naming_dict['pid'])
                    if pid not in hostapp_pids:
                        _remove_app_file(
                            op.join(pyrevit.PYREVIT_VERSION_APP_DIR,
                                    appdata_file)
                            )
                except Exception:
                    pass
