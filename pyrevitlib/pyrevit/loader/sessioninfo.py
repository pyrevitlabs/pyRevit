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
from pyrevit import runtime
from pyrevit.loader.systemdiag import system_diag


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


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
    envvars.set_pyrevit_env_var(envvars.VERSION_ENVVAR, pyrvt_ver)

    # set app version env var
    if HOST_APP.is_newer_than(2017):
        envvars.set_pyrevit_env_var(envvars.APPVERSION_ENVVAR,
                                    HOST_APP.subversion)
    else:
        envvars.set_pyrevit_env_var(envvars.APPVERSION_ENVVAR,
                                    HOST_APP.version)

    # set ironpython engine version env var
    attachment = user_config.get_current_attachment()
    if attachment and attachment.Clone:
        envvars.set_pyrevit_env_var(envvars.CLONENAME_ENVVAR,
                                    attachment.Clone.Name)
        envvars.set_pyrevit_env_var(envvars.IPYVERSION_ENVVAR,
                                    str(attachment.Engine.Version))
    else:
        mlogger.debug('Can not determine attachment.')
        envvars.set_pyrevit_env_var(envvars.CLONENAME_ENVVAR, "Unknown")
        envvars.set_pyrevit_env_var(envvars.IPYVERSION_ENVVAR, "0")

    # set cpython engine version env var
    cpyengine = user_config.get_active_cpython_engine()
    if cpyengine:
        envvars.set_pyrevit_env_var(envvars.CPYVERSION_ENVVAR,
                                    str(cpyengine.Version))
    else:
        envvars.set_pyrevit_env_var(envvars.CPYVERSION_ENVVAR, "0")

    # set a list of important assemblies
    # this is required for dotnet script execution
    set_loaded_pyrevit_referenced_modules(
        runtime.get_references()
        )


def get_runtime_info():
    """Return runtime information tuple.

    Returns:
        (RuntimeInfo): runtime info tuple

    Examples:
        ```python
        sessioninfo.get_runtime_info()
        ```
    """
    # FIXME: add example output
    return RuntimeInfo(
        pyrevit_version=envvars.get_pyrevit_env_var(envvars.VERSION_ENVVAR),
        engine_version=envvars.get_pyrevit_env_var(envvars.IPYVERSION_ENVVAR),
        host_version=envvars.get_pyrevit_env_var(envvars.APPVERSION_ENVVAR)
        )


def set_session_uuid(uuid_str):
    """Set session uuid on environment variable.

    Args:
        uuid_str (str): session uuid string
    """
    envvars.set_pyrevit_env_var(envvars.SESSIONUUID_ENVVAR, uuid_str)


def get_session_uuid():
    """Read session uuid from environment variable.

    Returns:
        (str): session uuid string
    """
    return envvars.get_pyrevit_env_var(envvars.SESSIONUUID_ENVVAR)


def new_session_uuid():
    """Create a new uuid for a pyRevit session.

    Returns:
        (str): session uuid string
    """
    uuid_str = safe_strtype(coreutils.new_uuid())
    set_session_uuid(uuid_str)
    return uuid_str


def get_loaded_pyrevit_assemblies():
    """Return list of loaded pyRevit assemblies from environment variable.

    Returns:
        (list[str]): list of loaded assemblies
    """
    # FIXME: verify and document return type
    loaded_assms_str = envvars.get_pyrevit_env_var(envvars.LOADEDASSMS_ENVVAR)
    if loaded_assms_str:
        return loaded_assms_str.split(coreutils.DEFAULT_SEPARATOR)
    else:
        return []


def set_loaded_pyrevit_assemblies(loaded_assm_name_list):
    """Set the environment variable with list of loaded assemblies.

    Args:
        loaded_assm_name_list (list[str]): list of assembly names
    """
    envvars.set_pyrevit_env_var(
        envvars.LOADEDASSMS_ENVVAR,
        coreutils.DEFAULT_SEPARATOR.join(loaded_assm_name_list)
        )


def get_loaded_pyrevit_referenced_modules():
    loaded_assms_str = envvars.get_pyrevit_env_var(envvars.REFEDASSMS_ENVVAR)
    if loaded_assms_str:
        return set(loaded_assms_str.split(coreutils.DEFAULT_SEPARATOR))
    else:
        return set()


def set_loaded_pyrevit_referenced_modules(loaded_assm_name_list):
    envvars.set_pyrevit_env_var(
        envvars.REFEDASSMS_ENVVAR,
        coreutils.DEFAULT_SEPARATOR.join(loaded_assm_name_list)
        )


def update_loaded_pyrevit_referenced_modules(loaded_assm_name_list):
    loaded_modules = get_loaded_pyrevit_referenced_modules()
    loaded_modules.update(loaded_assm_name_list)
    set_loaded_pyrevit_referenced_modules(loaded_modules)


def report_env():
    """Report python version, home directory, config file, etc."""
    # run diagnostics
    system_diag()

    # get python version that includes last commit hash
    mlogger.info('pyRevit version: %s - </> with :growing_heart: in %s',
                 envvars.get_pyrevit_env_var(envvars.VERSION_ENVVAR),
                 about.get_pyrevit_about().madein)

    if user_config.rocket_mode:
        mlogger.info('pyRevit Rocket Mode enabled. :rocket:')

    mlogger.info('Host is %s pid: %s', HOST_APP.pretty_name, HOST_APP.proc_id)
    # ipy 2.7.10 has a new line in its sys.version :rolling-eyes-emoji:
    mlogger.info('Running on: %s', sys.version.replace('\n', ' '))
    mlogger.info('User is: %s', HOST_APP.username)
    mlogger.info('Home Directory is: %s', HOME_DIR)
    mlogger.info('Session uuid is: %s', get_session_uuid())
    mlogger.info('Runtime assembly is: %s', runtime.RUNTIME_ASSM_NAME)
    mlogger.info('Config file is (%s): %s',
                 user_config.config_type, user_config.config_file)
