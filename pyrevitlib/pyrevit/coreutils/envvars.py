from pyrevit import PYREVIT_ADDON_NAME
from pyrevit.framework import AppDomain

# root env var dictionary key.
# must be the same in this file and pyrevit/loader/basetypes/_config.cs
# DomainStorageKeys.pyRevitEnvVarsDictKey
PYREVIT_ENV_VAR_DICT_NAME = 'pyRevitEnvVarsDict'


def get_pyrevit_env_vars():
    return AppDomain.CurrentDomain.GetData(PYREVIT_ENV_VAR_DICT_NAME)


def get_pyrevit_env_var(param_name):
    """Gets value of a parameter shared between all scripts.
    Some settings needs to be set for the current session and should affect
    the behaviour of all individual scripts inside the extensions.
    (e.g. If user activates the DEBUG mode, all scripts should follow
    and log the debug entries.)
    The information is saved using AppDomain.GetData and SetData in a
    dictionary parameter (PYREVIT_ENV_VAR_DICT_NAME). The dictionary is used
    to minimise the addition of named parameters to the AppDomain.
    The dictionary then includes all the internal parameters and their
    associated value. This way each script does not need to read
    the usersettings data which reduces file io and saves time.
    """

    # This function returns None if it can not find the parameter.
    # Thus value of None should not be used for params

    data_dict = AppDomain.CurrentDomain.GetData(PYREVIT_ENV_VAR_DICT_NAME)

    if data_dict:
        try:
            return data_dict[param_name]
        except KeyError:
            return None
    else:
        return None


def set_pyrevit_env_var(param_name, param_value):
    """Sets value of a parameter shared between all scripts.
    Some settings needs to be set for the current session and should affect
    the behaviour of all individual scripts inside the extensions.
    (e.g. If user activates the DEBUG mode, all scripts should follow
    and log the debug entries.)
    The information is saved using AppDomain.GetData and SetData in a
    dictionary parameter (PYREVIT_ENV_VAR_DICT_NAME). The dictionary is used
    to minimise the addition of named parameters to the AppDomain.
    The dictionary then includes all the internal parameters and their
    associated value. This way each script does not need to read the
    usersettings data which reduces file io and saves time.
    """
    # Get function returns None if it can not find the parameter.
    # Thus value of None should not be used for params

    data_dict = AppDomain.CurrentDomain.GetData(PYREVIT_ENV_VAR_DICT_NAME)

    if data_dict:
        data_dict[param_name] = param_value
    else:
        data_dict = {param_name: param_value}

    AppDomain.CurrentDomain.SetData(PYREVIT_ENV_VAR_DICT_NAME, data_dict)
