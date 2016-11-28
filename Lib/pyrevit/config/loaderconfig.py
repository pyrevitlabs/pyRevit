import os.path as op

from pyrevit.config import HOST_VERSION, HOST_USERNAME, PYREVIT_ASSEMBLY_NAME
from pyrevit.config import USER_TEMP_DIR

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process

# ----------------------------------------------------------------------------------------------------------------------
# session defaults
# ----------------------------------------------------------------------------------------------------------------------
SESSION_ID = "{}{}_{}".format(PYREVIT_ASSEMBLY_NAME, HOST_VERSION.version, HOST_USERNAME)

# creating a session id that is stamped with the process id of the Revit session.
# This id is unique for all python scripts running under this session.
# Previously the session id was stamped by formatted time
# SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, datetime.now().strftime('%y%m%d%H%M%S'))
SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, Process.GetCurrentProcess().Id)


# ----------------------------------------------------------------------------------------------------------------------
# asm maker defaults
# ----------------------------------------------------------------------------------------------------------------------
ASSEMBLY_FILE_TYPE = '.dll'
LOADER_ADDIN = 'PyRevitLoader'

# template python command class
LOADER_BASE_CLASSES_ASM = 'PyRevitBaseClasses'
LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommand')

# template python command availability class
LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS_NAME = 'PyRevitCommandDefaultAvail'
LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM,
                                                          LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS_NAME)
LOADER_ADDIN_COMMAND_CAT_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommandCategoryAvail')
LOADER_ADDIN_COMMAND_SEL_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommandSelectionAvail')


# ----------------------------------------------------------------------------------------------------------------------
# caching tabs, panels, buttons and button groups
# ----------------------------------------------------------------------------------------------------------------------
SUB_CMP_KEY = '_sub_components'
HASH_VALUE_PARAM = 'hash_value'
HASH_VERSION_PARAM = 'hash_version'

CACHE_TYPE_ASCII = 'ascii'
CACHE_TYPE_BINARY = 'binary'


# ----------------------------------------------------------------------------------------------------------------------
# script usage logging defaults
# ----------------------------------------------------------------------------------------------------------------------
# creating log file name from stamped session id
LOG_FILE_TYPE = '.log'
SESSION_LOG_FILE_NAME = SESSION_STAMPED_ID + LOG_FILE_TYPE
SESSION_LOG_FILE_PATH = op.join(USER_TEMP_DIR, SESSION_LOG_FILE_NAME)
LOG_ENTRY_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
