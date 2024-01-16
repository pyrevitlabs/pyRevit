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

Examples:
    ```python
    from pyrevit.coreutils import envvars
    envvars.set_pyrevit_env_var('MY_SCRIPT_STATUS', True)
    envvars.set_pyrevit_env_var('MY_SCRIPT_CONFIG', {'someconfig': True})
    ```

    Then another script or same script when executed later within the same
    session can query the shared environment variable:

    ```python
    envvars.get_pyrevit_env_vars('MY_SCRIPT_STATUS')
    ```
    True
    ```python
    envvars.get_pyrevit_env_vars('MY_SCRIPT_CONFIG')
    ```
    {'someconfig': True}
"""

from pyrevit.framework import AppDomain
from pyrevit.labs import Common

PRODUCT_NAME = str(Common.PyRevitLabsConsts.ProductName).upper()
# root env var dictionary key.
# must be the same in this file and pyrevit/loader/runtime/envvars.cs
ENV_VAR_DICT_NAME = PRODUCT_NAME + "EnvVarsDict"

SESSIONUUID_ENVVAR = PRODUCT_NAME + "_UUID"
APPVERSION_ENVVAR = PRODUCT_NAME + "_APPVERSION"
VERSION_ENVVAR = PRODUCT_NAME + "_VERSION"
CLONENAME_ENVVAR = PRODUCT_NAME + "_CLONE"
IPYVERSION_ENVVAR = PRODUCT_NAME + "_IPYVERSION"
CPYVERSION_ENVVAR = PRODUCT_NAME + "_CPYVERSION"

LOGGING_LEVEL_ENVVAR = PRODUCT_NAME + "_LOGGINGLEVEL"
FILELOGGING_ENVVAR = PRODUCT_NAME + "_FILELOGGING"

LOADEDASSMS_ENVVAR = PRODUCT_NAME + "_LOADEDASSMS"
REFEDASSMS_ENVVAR = PRODUCT_NAME + "_REFEDASSMS"

TELEMETRYSTATE_ENVVAR = PRODUCT_NAME + "_TELEMETRYSTATE"
TELEMETRYUTCTIMESTAMPS_ENVVAR = PRODUCT_NAME + "_TELEMETRYUTCTIMESTAMPS"
TELEMETRYDIR_ENVVAR = PRODUCT_NAME + "_TELEMETRYDIR"
TELEMETRYFILE_ENVVAR = PRODUCT_NAME + "_TELEMETRYFILE"
TELEMETRYSERVER_ENVVAR = PRODUCT_NAME + "_TELEMETRYSERVER"
TELEMETRYINCLUDEHOOKS_ENVVAR = PRODUCT_NAME + "_TELEMETRYINCLUDEHOOKS"

APPTELEMETRYSTATE_ENVVAR = PRODUCT_NAME + "_APPTELEMETRYSTATE"
APPTELEMETRYHANDLER_ENVVAR = \
    PRODUCT_NAME + "_APPTELEMETRYHANDLER"
APPTELEMETRYSERVER_ENVVAR = \
    PRODUCT_NAME + "_APPTELEMETRYSERVER"
APPTELEMETRYEVENTFLAGS_ENVVAR = \
    PRODUCT_NAME + "_APPTELEMETRYEVENTFLAGS"

ROUTES_SERVER = PRODUCT_NAME + "_ROUTESSERVER"
ROUTES_ROUTES = PRODUCT_NAME + "_ROUTESROUTES"

HOOKS_ENVVAR = PRODUCT_NAME + "_HOOKS"
HOOKSHANDLER_ENVVAR = PRODUCT_NAME + "_HOOKSHANDLER"

AUTOUPDATING_ENVVAR = PRODUCT_NAME + "_AUTOUPDATE"
OUTPUT_STYLESHEET_ENVVAR = PRODUCT_NAME + "_STYLESHEET"
RIBBONUPDATOR_ENVVAR = PRODUCT_NAME + "_RIBBONUPDATOR"
TABCOLORIZER_ENVVAR = PRODUCT_NAME + "_TABCOLORIZER"


def get_pyrevit_env_vars():
    """Get the root dictionary, holding all environment variables."""
    return AppDomain.CurrentDomain.GetData(ENV_VAR_DICT_NAME)


def get_pyrevit_env_var(param_name):
    """Get value of a parameter shared between all scripts.

    Args:
        param_name (str): name of environment variable

    Returns:
        (object): any object stored as the environment variable value
    """
    # This function returns None if it can not find the parameter.
    # Thus value of None should not be used for params

    data_dict = get_pyrevit_env_vars()
    return data_dict.get(param_name) if data_dict else None


def set_pyrevit_env_var(param_name, param_value):
    """Set value of a parameter shared between all scripts.

    Args:
        param_name (str): name of environment variable
        param_value (object): any python object
    """
    # Get function returns None if it can not find the parameter.
    # Thus value of None should not be used for params
    data_dict = get_pyrevit_env_vars() or {}
    data_dict[param_name] = param_value
    AppDomain.CurrentDomain.SetData(ENV_VAR_DICT_NAME, data_dict)
