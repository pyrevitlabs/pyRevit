"""
This module manages the usage logging system.

    This function is used to setup the usage logging system on pyRevit startup:
        >>> setup_usage_logfile()

    These functions are used to query information about the logging system:
        >>> get_default_usage_logfilepath()
        >>> get_current_usage_logpath()

        >>> get_current_usage_logfile()
        >>> get_current_usage_serverurl()
        >>> is_active()

    This module also provides a wrapper class around the command results
    dictionary that is included with the usage log record.

    Scripts should use the instance of this class provided by the
    scriptutils module. See scriptutils for examples

"""
import os.path as op

from pyrevit import PYREVIT_ADDON_NAME, PYREVIT_VERSION_APP_DIR,\
                    PYREVIT_FILE_PREFIX
from pyrevit.coreutils import is_blank
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars

from pyrevit.loader.sessioninfo import get_session_uuid
from pyrevit.userconfig import user_config


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


PYREVIT_USAGELOGSTATE_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_USAGELOGSTATE'
PYREVIT_USAGELOGFILE_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_USAGELOGFILE'
PYREVIT_USAGELOGSERVER_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_USAGELOGSERVER'


# templates for usage log file naming
FILE_LOG_EXT = 'json'
FILE_LOG_FILENAME_TEMPLATE = '{}_{}_usagelog.{}'


def _init_usagelogging_envvars():
    # init all env variables related to usage logging
    envvars.set_pyrevit_env_var(PYREVIT_USAGELOGSTATE_ENVVAR, False)
    envvars.set_pyrevit_env_var(PYREVIT_USAGELOGFILE_ENVVAR, '')
    envvars.set_pyrevit_env_var(PYREVIT_USAGELOGSERVER_ENVVAR, '')


def _disable_usage_logging():
    # set usage logging env variable to False, disabling the usage logging
    envvars.set_pyrevit_env_var(PYREVIT_USAGELOGSTATE_ENVVAR, False)


def _disable_file_usage_logging():
    # set file logging env variable to empty, disabling the file logging
    envvars.set_pyrevit_env_var(PYREVIT_USAGELOGFILE_ENVVAR, '')


def _disable_server_usage_logging():
    # set server logging env variable to empty, disabling the remote logging
    envvars.set_pyrevit_env_var(PYREVIT_USAGELOGSERVER_ENVVAR, '')


def _setup_default_logfile(usagelog_fullfilepath):
    # setup default usage logging file name
    envvars.set_pyrevit_env_var(
        PYREVIT_USAGELOGFILE_ENVVAR, usagelog_fullfilepath
        )
    if not op.exists(usagelog_fullfilepath):
        # if file does not exist, let's write the basic JSON list to it.
        try:
            with open(usagelog_fullfilepath, 'w') as log_file:
                log_file.write('[]')
        except Exception as write_err:
            mlogger.error('Usage logging is active but log file location '
                          'is not accessible. | %s', write_err)
            _disable_usage_logging()


def setup_usage_logfile(session_id=None):
    """Sets up the usage logging default config and environment values."""

    if not session_id:
        session_id = get_session_uuid()

    # default file path and name for usage logging
    filelogging_filename = FILE_LOG_FILENAME_TEMPLATE \
        .format(PYREVIT_FILE_PREFIX, session_id, FILE_LOG_EXT)

    # default server url for usage logging
    usagelog_serverurl = ''

    # initialize env variables related to usage logging
    _init_usagelogging_envvars()

    # setup config section if does not exist
    if not user_config.has_section('usagelogging'):
        user_config.add_section('usagelogging')

    # GLOBAL SWITCH ------------------------------------------------------------
    # setup default value for usage logging global switch
    ul_config = user_config.usagelogging
    usageloggingactive = ul_config.get_option('active', default_value=False)
    envvars.set_pyrevit_env_var(
        PYREVIT_USAGELOGSTATE_ENVVAR, usageloggingactive
        )

    # FILE usage logging -------------------------------------------------------
    # read or setup default values for file usage logging
    logfilepath = ul_config.get_option('logfilepath',
                                       default_value=PYREVIT_VERSION_APP_DIR)

    # check file usage logging config and setup destination
    if not logfilepath or is_blank(logfilepath):
        # if no config is provided, disable output
        _disable_file_usage_logging()
    else:
        # if config exists, create new usage log file under the same address
        if usageloggingactive:
            if op.isdir(logfilepath):
                # if directory is valid
                logfile_fullpath = op.join(logfilepath, filelogging_filename)
                _setup_default_logfile(logfile_fullpath)
            else:
                # if not, show error and disable usage logging
                mlogger.error('Provided usage log address does not exits or is '
                              'not a directory. Usage logging disabled.')
                _disable_usage_logging()

    # SERVER usage logging -----------------------------------------------------
    # read or setup default values for server usage logging
    logserverurl = ul_config.get_option('logserverurl',
                                        default_value=usagelog_serverurl)

    # check server usage logging config and setup destination
    if not logserverurl or is_blank(logserverurl):
        # if no config is provided, disable output
        _disable_server_usage_logging()
    else:
        # if config exists, setup server logging
        envvars.set_pyrevit_env_var(PYREVIT_USAGELOGSERVER_ENVVAR, logserverurl)


def get_default_usage_logfilepath():
    """Returns default usage logging path. This path is automatically
    generated at module execution.

    Returns:
        str: Default usage logging path. This might not be the active path.
    """
    return PYREVIT_VERSION_APP_DIR


def get_current_usage_logpath():
    """Returns active usage logging path. This path might be the default,
    or set by user in user config.

    Returns:
        str: Active usage logging path.
    """
    return op.dirname(envvars.get_pyrevit_env_var(PYREVIT_USAGELOGFILE_ENVVAR))


def get_current_usage_logfile():
    """
    Returns active usage logging full file path. This is the file that usage
    logs are being written to in current pyRevit session. Usage logging
    filenames are automatically generated at this module execution.

    Returns:
        str: Active usage logging full file path.
    """
    return envvars.get_pyrevit_env_var(PYREVIT_USAGELOGFILE_ENVVAR)


def get_current_usage_serverurl():
    """
    Returns active usage logging server url. This is the server that usage
    logs are being sent to in current pyRevit session.
    Server url must be set by the user in config.

    Returns:
        str: Active usage logging server url.
    """
    return envvars.get_pyrevit_env_var(PYREVIT_USAGELOGSERVER_ENVVAR)


def is_active():
    """Returns status of usage logging system.

    Returns:
        bool: True if usage logging is active, False if not.
    """
    return envvars.get_pyrevit_env_var(PYREVIT_USAGELOGSTATE_ENVVAR)
