import sys
import uuid

from pyrevit import PYREVIT_ADDON_NAME, HOST_APP, HOME_DIR

from pyrevit.versionmgr import PYREVIT_VERSION
from pyrevit.coreutils import DEFAULT_SEPARATOR
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.envvars import set_pyrevit_env_var, get_pyrevit_env_var
from pyrevit.userconfig import user_config

from pyrevit.loader.basetypes import BASE_TYPES_ASM_NAME


logger = get_logger(__name__)


SESSION_UUID_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_uuidISC'

LOADEDASSM_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_loadedassms'
LOADEDASSM_COUNT_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_assmcount'


def set_session_uuid(uuid_str):
    set_pyrevit_env_var(SESSION_UUID_ISC_KEYNAME, uuid_str)


def get_session_uuid():
    return get_pyrevit_env_var(SESSION_UUID_ISC_KEYNAME)


def new_session_uuid():
    uuid_str = unicode(uuid.uuid1())
    set_session_uuid(uuid_str)
    return uuid_str


def get_total_loaded_assm_count():
    """Returns the total number of pyRevit assemblies loaded under current
    Revit session. This value is stored in an environment variable and is kept
    updated during the multiple pyRevit sessions. Notice that not all of these
    assemblies belong to current pyRevit session as pyRevit could be reloaded
     multiple times under the same Revit session.

    Returns:
        total count (int): Total number of loaded assemblies.
    """
    assm_count = get_pyrevit_env_var(LOADEDASSM_COUNT_ISC_KEYNAME)
    if not assm_count:
        return 0
    else:
        return assm_count


def set_total_loaded_assm_count(assm_count):
    """Sets the total number of pyRevit assemblies loaded under current
    Revit session. This value is stored in an environment variable and is kept
    updated during the multiple pyRevit sessions.

    This value should not be updated by pyRevit users.

    Args:
        assm_count (int): Number of loaded assemblies
    """

    set_pyrevit_env_var(LOADEDASSM_COUNT_ISC_KEYNAME, assm_count)


def get_loaded_pyrevit_assemblies():
    loaded_assms_str = get_pyrevit_env_var(LOADEDASSM_ISC_KEYNAME)
    if loaded_assms_str:
        return loaded_assms_str.split(DEFAULT_SEPARATOR)
    else:
        return []


def set_loaded_pyrevit_assemblies(loaded_assm_name_list):
    set_pyrevit_env_var(LOADEDASSM_ISC_KEYNAME,
                        DEFAULT_SEPARATOR.join(loaded_assm_name_list))

    set_total_loaded_assm_count(get_total_loaded_assm_count()
                                + len(loaded_assm_name_list))


def system_diag():
    """Verifies system status is appropriate for a pyRevit session.
    """

    # checking available drive space
    import ctypes
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p("."), None,
                                               None, ctypes.pointer(free_bytes))

    free_hd_space = float(free_bytes.value) / (1024 ** 3)
    if free_hd_space < 10.0:
        logger.warning('Remaining space on local drive is less than 10GB...')


def report_env():
    # log python version, home directory, config file, ...
    # get python version that includes last commit hash
    pyrvt_ver = PYREVIT_VERSION.get_formatted()

    system_diag()

    logger.info('pyRevit version: {} - '
                ':coded: with :small-black-heart: '
                'in Portland, OR'.format(pyrvt_ver))
    logger.info('Host is {} (build: {} id: {})'.format(HOST_APP.version_name,
                                                       HOST_APP.build,
                                                       HOST_APP.proc_id))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Session uuid is: {}'.format(get_session_uuid()))
    logger.info('Base assembly is: {}'.format(BASE_TYPES_ASM_NAME))
    logger.info('Config file is: {}'.format(user_config.config_file))
