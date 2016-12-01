import os
import os.path as op

from pyrevit import USER_ROAMING_DIR, PYREVIT_ADDON_NAME, HOST_VERSION, HOST_USERNAME
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


APPDATA_FILE_PREFIX = '{}_{}_{}'.format(PYREVIT_ADDON_NAME, HOST_VERSION, HOST_USERNAME)
APPDATA_TEMP_FILE_PREFIX = 'TEMP_{}'.format(APPDATA_FILE_PREFIX)


def get_temp_file(file_id='noid', file_ext='tmp'):
    """
    Get full file path to a file that is temporary and will be cleaned up between sessions.

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension

    Returns:
        str: Full file path
    """
    full_filename = '{}_{}.{}'.format(APPDATA_FILE_PREFIX, file_id, file_ext)
    return op.join(PYREVIT_APP_DIR, full_filename)


def get_data_file(file_id=None, file_ext='tmp'):
    """
    Get full file path to a file that will not be cleaned up between sessions.

    Args:
        file_id (str): Unique identifier for the file
        file_ext (str): File extension

    Returns:
        str: Full file path
    """
    full_filename = '{}_{}.{}'.format(APPDATA_FILE_PREFIX, file_id, file_ext)
    return op.join(PYREVIT_APP_DIR, full_filename)
