"""Session info."""
import sys

from pyrevit import HOST_APP, HOME_DIR

from pyrevit import versionmgr
from pyrevit.compat import safe_strtype
from pyrevit.versionmgr import about
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.userconfig import user_config

from pyrevit.loader.basetypes import BASE_TYPES_ASM_NAME
from pyrevit.loader.systemdiag import system_diag


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


PYREVIT_SESSIONUUID_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_UUID'
PYREVIT_LOADEDASSMS_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_LOADEDASSMS'
PYREVIT_LOADEDASSMCOUNT_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_ASSMCOUNT'


def set_session_uuid(uuid_str):
    envvars.set_pyrevit_env_var(PYREVIT_SESSIONUUID_ENVVAR, uuid_str)


def get_session_uuid():
    return envvars.get_pyrevit_env_var(PYREVIT_SESSIONUUID_ENVVAR)


def new_session_uuid():
    uuid_str = safe_strtype(coreutils.new_uuid())
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
        return loaded_assms_str.split(coreutils.DEFAULT_SEPARATOR)
    else:
        return []


def set_loaded_pyrevit_assemblies(loaded_assm_name_list):
    envvars.set_pyrevit_env_var(
        PYREVIT_LOADEDASSMS_ENVVAR,
        coreutils.DEFAULT_SEPARATOR.join(loaded_assm_name_list)
        )

    set_total_loaded_assm_count(get_total_loaded_assm_count()
                                + len(loaded_assm_name_list))


def report_env():
    # log python version, home directory, config file, ...
    # get python version that includes last commit hash
    pyrvt_ver = versionmgr.get_pyrevit_version().get_formatted()

    system_diag()

    mlogger.info('pyRevit version: %s - </> with :growing_heart: in %s',
                 pyrvt_ver, about.get_pyrevit_about().madein)
    if user_config.core.get_option('rocketmode', False):
        mlogger.info('pyRevit Rocket Mode enabled. :rocket:')

    if HOST_APP.is_newer_than(2017):
        full_host_name = \
            HOST_APP.version_name.replace(HOST_APP.version,
                                          HOST_APP.subversion)
    else:
        full_host_name = HOST_APP.version_name
    mlogger.info('Host is %s (build: %s id: %s)',
                 full_host_name, HOST_APP.build, HOST_APP.proc_id)
    mlogger.info('Running on: %s', sys.version)
    mlogger.info('User is: %s', HOST_APP.username)
    mlogger.info('Home Directory is: %s', HOME_DIR)
    mlogger.info('Session uuid is: %s', get_session_uuid())
    mlogger.info('Base assembly is: %s', BASE_TYPES_ASM_NAME)
    mlogger.info('Config file is (%s): %s',
                 user_config.config_type, user_config.config_file)
