"""
This module manages the telemetry system.

    This function is used to setup the telemetry system on pyRevit startup:
        >>> setup_telemetry()

    These functions are used to query information about the logging system:
        >>> get_telemetry_state()

        >>> get_apptelemetry_state()

    This module also provides a wrapper class around the command results
    dictionary that is included with the telemetry record.

    Scripts should use the instance of this class provided by the
    script module. See `script.get_results()` for examples
"""
import os.path as op

from pyrevit import PYREVIT_ADDON_NAME, PYREVIT_VERSION_APP_DIR,\
                    PYREVIT_FILE_PREFIX
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars

from pyrevit.loader.sessioninfo import get_session_uuid
from pyrevit.userconfig import user_config

from pyrevit.labs import TargetApps


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)

consts = TargetApps.Revit.PyRevitConsts

PYREVIT_TELEMETRYSTATE_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_TELEMETRYSTATE'
PYREVIT_TELEMETRYDIR_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_TELEMETRYDIR'
PYREVIT_TELEMETRYFILE_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_TELEMETRYFILE'
PYREVIT_TELEMETRYSERVER_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_TELEMETRYSERVER'

PYREVIT_APPTELEMETRYSTATE_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_APPTELEMETRYSTATE'
PYREVIT_APPTELEMETRYSERVER_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_APPTELEMETRYSERVER'


# templates for telemetry file naming
FILE_LOG_EXT = 'json'
FILE_LOG_FILENAME_TEMPLATE = '{}_{}_telemetry.{}'


def _get_telemetry_configs(configs):
    # setup config section if does not exist
    if not configs.has_section(consts.ConfigsTelemetrySection):
        configs.add_section(consts.ConfigsTelemetrySection)
    return configs.telemetry


def get_default_telemetry_filepath():
    return PYREVIT_VERSION_APP_DIR


def get_telemetry_state():
    return envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYSTATE_ENVVAR)


def get_telemetry_file_dir():
    return envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYDIR_ENVVAR)


def get_telemetry_file_path():
    return envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYFILE_ENVVAR)


def get_telemetry_server_url():
    return envvars.get_pyrevit_env_var(PYREVIT_TELEMETRYSERVER_ENVVAR)


def set_telemetry_state(state, configs=None):
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYSTATE_ENVVAR, state)
    if configs:
        tc = _get_telemetry_configs(configs)
        tc.set_option(consts.ConfigsTelemetryStatusKey, state)


def set_telemetry_file_dir(file_dir, configs=None):
    if op.isdir(file_dir):
        envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYDIR_ENVVAR, file_dir)
        if configs:
            tc = _get_telemetry_configs(configs)
            tc.set_option(consts.ConfigsTelemetryFilePathKey, file_dir)


def set_telemetry_file_path(file_path):
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYFILE_ENVVAR, file_path)


def set_telemetry_server_url(server_url, configs=None):
    envvars.set_pyrevit_env_var(PYREVIT_TELEMETRYSERVER_ENVVAR, server_url)
    if configs:
        tc = _get_telemetry_configs(configs)
        tc.set_option(consts.ConfigsTelemetryServerUrlKey, server_url)


def disable_telemetry():
    set_telemetry_state(False)


def disable_telemetry_to_file():
    set_telemetry_file_path('')


def disable_telemetry_to_server():
    set_telemetry_server_url('')


def get_apptelemetry_state():
    return envvars.get_pyrevit_env_var(PYREVIT_APPTELEMETRYSTATE_ENVVAR)


def set_apptelemetry_state(state, configs=None):
    envvars.set_pyrevit_env_var(PYREVIT_APPTELEMETRYSTATE_ENVVAR, state)
    if configs:
        tc = _get_telemetry_configs(configs)
        tc.set_option(consts.ConfigsAppTelemetryStatusKey, state)


def get_apptelemetry_server_url():
    return envvars.get_pyrevit_env_var(PYREVIT_APPTELEMETRYSERVER_ENVVAR)


def get_apptelemetry_event_config():
    # TODO: get_apptelemetry_event_config
    pass


def set_apptelemetry_server_url(server_url, configs=None):
    envvars.set_pyrevit_env_var(PYREVIT_APPTELEMETRYSERVER_ENVVAR, server_url)
    if configs:
        tc = _get_telemetry_configs(configs)
        tc.set_option(consts.ConfigsAppTelemetryServerUrlKey, server_url)


def set_apptelemetry_event_config(event_config):
    # TODO: set_apptelemetry_event_config
    pass


def disable_apptelemetry():
    set_apptelemetry_state(False)


def disable_apptelemetry_to_server():
    set_apptelemetry_server_url('')


def _setup_default_logfile(telemetry_fullpath):
    # setup default telemetry file name
    if not op.exists(telemetry_fullpath):
        # if file does not exist, let's write the basic JSON list to it.
        with open(telemetry_fullpath, 'w') as log_file:
            log_file.write('[]')


def setup_telemetry(session_id=None):
    """Sets up the telemetry default config and environment values."""

    # make sure session id is availabe
    if not session_id:
        session_id = get_session_uuid()

    telemetry_config = _get_telemetry_configs(user_config)

    # PYREVIT TELEMETRY -------------------------------------------------------
    # global state
    telemetry_state = \
        telemetry_config.get_option(consts.ConfigsTelemetryStatusKey,
                                    default_value=False)
    set_telemetry_state(telemetry_state)

    # read or setup default values for file telemetry
    # default file path and name for telemetry
    telemetry_file_dir = \
        telemetry_config.get_option(
            consts.ConfigsTelemetryFilePathKey,
            default_value=get_default_telemetry_filepath())
    set_telemetry_file_dir(telemetry_file_dir)

    # check file telemetry config and setup destination
    if not telemetry_file_dir or coreutils.is_blank(telemetry_file_dir):
        # if no config is provided, disable output
        disable_telemetry_to_file()
    # if config exists, create new telemetry file under the same address
    elif telemetry_state:
        if op.isdir(telemetry_file_dir):
            telemetry_file_name = \
                FILE_LOG_FILENAME_TEMPLATE.format(PYREVIT_FILE_PREFIX,
                                                  session_id,
                                                  FILE_LOG_EXT)
            # if directory is valid
            telemetry_fullfilepath = \
                op.join(telemetry_file_dir, telemetry_file_name)
            set_telemetry_file_path(telemetry_fullfilepath)
            # setup telemetry file or disable if failed
            try:
                _setup_default_logfile(telemetry_fullfilepath)
            except Exception as write_err:
                mlogger.error('Telemetry is active but log file location '
                              'is not accessible. | %s', write_err)
                disable_telemetry_to_file()
        else:
            # if not, show error and disable telemetry
            mlogger.error('Provided telemetry address does not exits or is '
                          'not a directory. Telemetry disabled.')
            disable_telemetry_to_file()

    # read or setup default values for server telemetry
    telemetry_server_url = \
        telemetry_config.get_option(consts.ConfigsTelemetryServerUrlKey,
                                    default_value='')

    # check server telemetry config and setup destination
    if not telemetry_server_url or coreutils.is_blank(telemetry_server_url):
        # if no config is provided, disable output
        disable_telemetry_to_server()
    else:
        # if config exists, setup server logging
        set_telemetry_server_url(telemetry_server_url)

    # APP TELEMETRY ------------------------------------------------------------
    # setup default value for telemetry global switch
    apptelemetry_state = \
        telemetry_config.get_option(consts.ConfigsAppTelemetryStatusKey,
                                    default_value=False)
    set_apptelemetry_state(apptelemetry_state)

    # read or setup default values for server telemetry
    apptelemetry_server_url = \
        telemetry_config.get_option(consts.ConfigsAppTelemetryServerUrlKey,
                                    default_value='')

    # check server telemetry config and setup destination
    if not apptelemetry_server_url \
            or coreutils.is_blank(apptelemetry_server_url):
        # if no config is provided, disable output
        disable_apptelemetry_to_server()
    else:
        # if config exists, setup server logging
        set_apptelemetry_server_url(apptelemetry_server_url)

    user_config.save_changes()
