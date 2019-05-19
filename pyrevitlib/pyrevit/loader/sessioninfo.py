"""Manage information about pyRevit sessions."""
import sys
from collections import namedtuple

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

PYREVIT_VERSION_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_VERSION'
PYREVIT_APPVERSION_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_APPVERSION'
PYREVIT_IPYVERSION_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_IPYVERSION'
PYREVIT_CSPYVERSION_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_CPYVERSION'


RuntimeInfo = namedtuple('RuntimeInfo', ['pyrevit_version',
                                         'engine_version',
                                         'host_version'])
"""Session runtime information tuple.

Args:
    pyrevit_version (str): formatted pyRevit version
    engine_version (int): active IronPython engine version
    host_version (str): Current Revit version
"""


def setup_runtime_vars():
    """Setup runtime environment variables with session information."""
    # set pyrevit version
    pyrvt_ver = versionmgr.get_pyrevit_version().get_formatted()
    envvars.set_pyrevit_env_var(PYREVIT_VERSION_ENVVAR, pyrvt_ver)

    # set app version env var
    if HOST_APP.is_newer_than(2017):
        envvars.set_pyrevit_env_var(PYREVIT_APPVERSION_ENVVAR,
                                    HOST_APP.subversion)
    else:
        envvars.set_pyrevit_env_var(PYREVIT_APPVERSION_ENVVAR,
                                    HOST_APP.version)

    # set ironpython engine version env var
    attachment = user_config.get_current_attachment()
    if attachment and attachment.Clone:
        envvars.set_pyrevit_env_var(PYREVIT_IPYVERSION_ENVVAR,
                                    attachment.Engine.Version)

    # set cpython engine version env var
    cpyengine = user_config.get_active_cpython_engine()
    if cpyengine:
        envvars.set_pyrevit_env_var(PYREVIT_CSPYVERSION_ENVVAR,
                                    cpyengine.Version)


def get_runtime_info():
    """Return runtime information tuple.

    Returns:
        :obj:`RuntimeInfo`: runtime info tuple

    Example:
        >>> sessioninfo.get_runtime_info()
    """
    # FIXME: add example output
    return RuntimeInfo(
        pyrevit_version=envvars.get_pyrevit_env_var(PYREVIT_VERSION_ENVVAR),
        engine_version=envvars.get_pyrevit_env_var(PYREVIT_IPYVERSION_ENVVAR),
        host_version=envvars.get_pyrevit_env_var(PYREVIT_APPVERSION_ENVVAR)
        )


def set_session_uuid(uuid_str):
    """Set session uuid on environment variable.

    Args:
        uuid_str (str): session uuid string
    """
    envvars.set_pyrevit_env_var(PYREVIT_SESSIONUUID_ENVVAR, uuid_str)


def get_session_uuid():
    """Read session uuid from environment variable.

    Returns:
        str: session uuid string
    """
    return envvars.get_pyrevit_env_var(PYREVIT_SESSIONUUID_ENVVAR)


def new_session_uuid():
    """Create a new uuid for a pyRevit session.

    Returns:
        str: session uuid string
    """
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
        int: Total number of loaded assemblies.
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
        assm_count (int): assembly count
    """
    envvars.set_pyrevit_env_var(PYREVIT_LOADEDASSMCOUNT_ENVVAR, assm_count)


def get_loaded_pyrevit_assemblies():
    """Return list of loaded pyRevit assemblies from environment variable.

    Returns:
        list[str]: list of loaded assemblies
    """
    # FIXME: verify and document return type
    loaded_assms_str = envvars.get_pyrevit_env_var(PYREVIT_LOADEDASSMS_ENVVAR)
    if loaded_assms_str:
        return loaded_assms_str.split(coreutils.DEFAULT_SEPARATOR)
    else:
        return []


def set_loaded_pyrevit_assemblies(loaded_assm_name_list):
    """Set the environment variable with list of loaded assemblies.

    Args:
        loaded_assm_name_list (list[str]): list of assembly names
        val (type): desc
    """
    envvars.set_pyrevit_env_var(
        PYREVIT_LOADEDASSMS_ENVVAR,
        coreutils.DEFAULT_SEPARATOR.join(loaded_assm_name_list)
        )

    set_total_loaded_assm_count(get_total_loaded_assm_count()
                                + len(loaded_assm_name_list))


def report_env():
    """Report python version, home directory, config file, etc."""
    # run diagnostics
    system_diag()

    # get python version that includes last commit hash
    mlogger.info('pyRevit version: %s - </> with :growing_heart: in %s',
                 envvars.get_pyrevit_env_var(PYREVIT_VERSION_ENVVAR),
                 about.get_pyrevit_about().madein)

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
