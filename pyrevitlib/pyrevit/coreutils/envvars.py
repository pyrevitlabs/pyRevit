"""pyRevit managed environment variables framework.

pyRevit provides the environment variables framework to the pyRevit core
and all pyRevit tools so they can store arbitary data withing the running host
session and share small data quickly between script runs.

Some settings needs to be set for the current session and might need to affect
the behaviour of all individual scripts inside the extensions.
(e.g. If user activates the ``DEBUG`` mode, all scripts should follow and log
the debug entries.) The information is saved using ``AppDomain.GetData`` and
``SetData`` in a dictionary parameter. The dictionary is used to minimize the
addition of named parameters to the AppDomain. The dictionary then includes
all the internal parameters and their associated value. This way each script
does not need to read the usersettings data which reduces io and saves time.


pyRevit uses environment variables extensively at its core and making changes
to the core environment variables (starting with ``PYREVIT_``) through
scripts is strongly prohibited.

Example:
    >>> from pyrevit.coreutils import envvars
    >>> envvars.set_pyrevit_env_var('MY_SCRIPT_STATUS', True)
    >>> envvars.set_pyrevit_env_var('MY_SCRIPT_CONFIG', {'someconfig': True})

    Then another script or same script when executed later within the same
    session can query the shared environment variable:

    >>> envvars.get_pyrevit_env_vars('MY_SCRIPT_STATUS')
    True
    >>> envvars.get_pyrevit_env_vars('MY_SCRIPT_CONFIG')
    {'someconfig': True}
"""

from pyrevit.framework import AppDomain
from pyrevit.labs import PyRevit

# root env var dictionary key.
# must be the same in this file and pyrevit/loader/basetypes/envvars.cs
ENV_VAR_DICT_NAME = PyRevit.PyRevit.ProductName + "EnvVarsDict"

SESSIONUUID_ENVVAR = PyRevit.PyRevit.ProductName + "_UUID"
APPVERSION_ENVVAR = PyRevit.PyRevit.ProductName + "_APPVERSION"
VERSION_ENVVAR = PyRevit.PyRevit.ProductName + "_VERSION"
CLONENAME_ENVVAR = PyRevit.PyRevit.ProductName + "_CLONE"
IPYVERSION_ENVVAR = PyRevit.PyRevit.ProductName + "_IPYVERSION"
CPYVERSION_ENVVAR = PyRevit.PyRevit.ProductName + "_CPYVERSION"

LOGGING_LEVEL_ENVVAR = PyRevit.PyRevit.ProductName + "_LOGGINGLEVEL"
FILELOGGING_ENVVAR = PyRevit.PyRevit.ProductName + "_FILELOGGING"

LOADEDASSMS_ENVVAR = PyRevit.PyRevit.ProductName + "_LOADEDASSMS"
REFEDASSMS_ENVVAR = PyRevit.PyRevit.ProductName + "_REFEDASSMS"

TELEMETRYSTATE_ENVVAR = PyRevit.PyRevit.ProductName + "_TELEMETRYSTATE"
TELEMETRYDIR_ENVVAR = PyRevit.PyRevit.ProductName + "_TELEMETRYDIR"
TELEMETRYFILE_ENVVAR = PyRevit.PyRevit.ProductName + "_TELEMETRYFILE"
TELEMETRYSERVER_ENVVAR = PyRevit.PyRevit.ProductName + "_TELEMETRYSERVER"

APPTELEMETRYSTATE_ENVVAR = PyRevit.PyRevit.ProductName + "_APPTELEMETRYSTATE"
APPTELEMETRYHANDLER_ENVVAR = \
    PyRevit.PyRevit.ProductName + "_APPTELEMETRYHANDLER"
APPTELEMETRYSERVER_ENVVAR = \
    PyRevit.PyRevit.ProductName + "_APPTELEMETRYSERVER"
APPTELEMETRYEVENTFLAGS_ENVVAR = \
    PyRevit.PyRevit.ProductName + "_APPTELEMETRYEVENTFLAGS"

HOOKS_ENVVAR = PyRevit.PyRevit.ProductName + "_HOOKS"
HOOKSHANDLER_ENVVAR = PyRevit.PyRevit.ProductName + "_HOOKSHANDLER"

AUTOUPDATING_ENVVAR = PyRevit.PyRevit.ProductName + "_AUTOUPDATE"
OUTPUT_STYLESHEET_ENVVAR = PyRevit.PyRevit.ProductName + "_STYLESHEET"


def get_pyrevit_env_vars():
    """Get the root dictionary, holding all environment variables."""
    return AppDomain.CurrentDomain.GetData(ENV_VAR_DICT_NAME)


def get_pyrevit_env_var(param_name):
    """Get value of a parameter shared between all scripts.

    Args:
        param_name (str): name of environment variable

    Returns:
        object: any object stored as the environment variable value
    """
    # This function returns None if it can not find the parameter.
    # Thus value of None should not be used for params

    data_dict = AppDomain.CurrentDomain.GetData(ENV_VAR_DICT_NAME)

    if data_dict:
        try:
            return data_dict[param_name]
        except KeyError:
            return None
    else:
        return None


def set_pyrevit_env_var(param_name, param_value):
    """Set value of a parameter shared between all scripts.

    Args:
        param_name (str): name of environment variable
        param_value (object): any python object
    """
    # Get function returns None if it can not find the parameter.
    # Thus value of None should not be used for params
    data_dict = AppDomain.CurrentDomain.GetData(ENV_VAR_DICT_NAME)

    if data_dict:
        data_dict[param_name] = param_value
    else:
        data_dict = {param_name: param_value}

    AppDomain.CurrentDomain.SetData(ENV_VAR_DICT_NAME, data_dict)
