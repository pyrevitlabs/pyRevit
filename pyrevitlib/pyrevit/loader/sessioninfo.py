import sys
import uuid

from pyrevit import PYREVIT_ADDON_NAME, HOST_APP, HOME_DIR

from pyrevit import versionmgr
from pyrevit.versionmgr import about
from pyrevit.coreutils import DEFAULT_SEPARATOR
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.userconfig import user_config

from pyrevit.loader.basetypes import BASE_TYPES_ASM_NAME
from pyrevit.loader.systemdiag import system_diag


logger = get_logger(__name__)


PYREVIT_SESSIONUUID_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_UUID'
PYREVIT_LOADEDASSMS_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_LOADEDASSMS'
PYREVIT_LOADEDASSMCOUNT_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_ASSMCOUNT'


def set_session_uuid(uuid_str):
    envvars.set_pyrevit_env_var(PYREVIT_SESSIONUUID_ENVVAR, uuid_str)


def get_session_uuid():
    return envvars.get_pyrevit_env_var(PYREVIT_SESSIONUUID_ENVVAR)


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
    assm_count = envvars.get_pyrevit_env_var(PYREVIT_LOADEDASSMCOUNT_ENVVAR)
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

    envvars.set_pyrevit_env_var(PYREVIT_LOADEDASSMCOUNT_ENVVAR, assm_count)


def get_loaded_pyrevit_assemblies():
    loaded_assms_str = envvars.get_pyrevit_env_var(PYREVIT_LOADEDASSMS_ENVVAR)
    if loaded_assms_str:
        return loaded_assms_str.split(DEFAULT_SEPARATOR)
    else:
        return []


def set_loaded_pyrevit_assemblies(loaded_assm_name_list):
    envvars.set_pyrevit_env_var(PYREVIT_LOADEDASSMS_ENVVAR,
                        DEFAULT_SEPARATOR.join(loaded_assm_name_list))

    set_total_loaded_assm_count(get_total_loaded_assm_count()
                                + len(loaded_assm_name_list))


def report_env():
    # log python version, home directory, config file, ...
    # get python version that includes last commit hash
    pyrvt_ver = versionmgr.get_pyrevit_version().get_formatted()

    system_diag()

    logger.info('pyRevit version: {} - '
                ':coded: with :small-black-heart: '
                'in {}'.format(pyrvt_ver, about.get_pyrevit_about().madein))
    if user_config.core.get_option('rocketmode', False):
        logger.info('pyRevit Rocket Mode enabled. :rocket:')
    logger.info('Host is {} (build: {} id: {})'.format(HOST_APP.version_name,
                                                       HOST_APP.build,
                                                       HOST_APP.proc_id))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Session uuid is: {}'.format(get_session_uuid()))
    logger.info('Base assembly is: {}'.format(BASE_TYPES_ASM_NAME))
    logger.info('Config file is: {}'.format(user_config.config_file))
