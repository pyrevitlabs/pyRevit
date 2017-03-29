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

    This module also provides a wrapper class around the command results dictionary that is included
    with the usage log record.
        >>> CommandCustomResults()
    Scripts should use the instance of this class provided by the scriptutils module.
    See scriptutils for examples

"""

import os
import os.path as op

from pyrevit import EXEC_PARAMS
from pyrevit import PYREVIT_ADDON_NAME, PYREVIT_VERSION_APP_DIR, PYREVIT_FILE_PREFIX
from pyrevit.coreutils import is_blank
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.envvars import set_pyrevit_env_var, get_pyrevit_env_var

from pyrevit.loader.sessioninfo import get_session_uuid
from pyrevit.userconfig import user_config


logger = get_logger(__name__)


# environment parameter names for communicating usage logging with
# the command executor and usage logger in c-sharp
USAGELOG_STATE_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_usagelogstateISC'
USAGELOG_FILEPATH_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_usagelogfileISC'
USAGELOG_SERVERURL_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_usagelogserverISC'

# default file path and name for usage logging
FILE_LOG_EXT = 'json'
FILE_LOG_FILENAME = '{}_{}_usagelog.{}'.format(PYREVIT_FILE_PREFIX, get_session_uuid(), FILE_LOG_EXT)
USAGELOG_FILEPATH = op.join(PYREVIT_VERSION_APP_DIR, FILE_LOG_FILENAME)

# default server url for usage logging
USAGELOG_SERVERURL = ''


class _CommandCustomResults(object):
    """
    This class provides an interface wrapper around the EXEC_PARAMS.result_dict dictionary that is
    provided by the ScriptExecutor C# object. ScriptExecutor provides this results dictionary to all
    scripts, and scripts can add key:value pairs to the dictionary. But since the provided dictionary is
    a C# dictionary, this class provides a very easy to use wrapper around it.

    Example:
        >>> CommandCustomResults().returnparam = value

    Attributes:
        any (str): This is a smart class and can accept any attribute other than the reserved ones.
    """

    # list of standard/default usage log record params provided by the c-sharp logger
    # scripts should not use these names
    RESERVED_NAMES = ['time', 'username', 'revit', 'revitbuild', 'sessionid', 'pyrevit', 'debug',
                      'alternate', 'commandname', 'result', 'source']

    def __getattr__(self, key):
        # return value of the given key, let it raise exception if the value is not there
        return unicode(EXEC_PARAMS.result_dict[key])

    def __setattr__(self, key, value):
        if key in CommandCustomResults.RESERVED_NAMES:
            # making sure the script is not using a reserved name
            logger.error('{} is a standard log param. Can not override this value.'.format(key))
        else:
            # if all is okay lets add the key:value to the return dict
            EXEC_PARAMS.result_dict.Add(key, unicode(value))


def _init_usagelogging_envvars():
    # init all env variables related to usage logging
    set_pyrevit_env_var(USAGELOG_STATE_ISC_KEYNAME, False)
    set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, '')
    set_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME, '')


def _disable_usage_logging():
    # set usage logging env variable to False, disabling the usage logging
    set_pyrevit_env_var(USAGELOG_STATE_ISC_KEYNAME, False)


def _disable_file_usage_logging():
    # set file logging env variable to empty, disabling the file logging
    set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, '')


def _disable_server_usage_logging():
    # set server logging env variable to empty, disabling the remote logging
    set_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME, '')


def _setup_default_logfile():
    # setup default usage logging file name
    set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, USAGELOG_FILEPATH)
    if not op.exists(USAGELOG_FILEPATH):
        # if file does not exist, let's write the basic JSON list to it.
        try:
            with open(USAGELOG_FILEPATH, 'w') as log_file:
                log_file.write('[]')
        except Exception as write_err:
            logger.error('Usage logging is active but log file location is not accessible. | {}'.format(write_err))
            _disable_usage_logging()


def setup_usage_logfile():
    """Sets up the usage logging default config and environment values."""

    # initialize env variables related to usage logging
    _init_usagelogging_envvars()

    # setup config section if does not exist
    if not user_config.has_section('usagelogging'):
        user_config.add_section('usagelogging')

    # setup default value for usage logging global switch
    usageloggingactive = user_config.usagelogging.get_option('active', default_value=False)
    set_pyrevit_env_var(USAGELOG_STATE_ISC_KEYNAME, usageloggingactive)

    # read or setup default values for file and server usage logging
    logfilepath = user_config.usagelogging.get_option('logfilepath', default_value=USAGELOG_FILEPATH)
    logserverurl = user_config.usagelogging.get_option('logserverurl', default_value=USAGELOG_SERVERURL)

    # FILE usage logging
    # check file usage logging config and setup destination
    if not logfilepath or is_blank(logfilepath):
        # if no config is provided, disable output
        _disable_file_usage_logging()
    else:
        # if config exists, create new usage log file under the same address
        if op.isdir(logfilepath):
            # if directory is valid
            logfile_fullpath = op.join(logfilepath, FILE_LOG_FILENAME)
            set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, logfile_fullpath)
        else:
            # if not, show error and disable usage logging
            logger.error('Provided usage log address does not exits or is not a directory. Usage logging disabled.')
            _disable_usage_logging()

    # SERVER usage logging
    # check server usage logging config and setup destination
    if not logserverurl or is_blank(logserverurl):
        # if no config is provided, disable output
        _disable_server_usage_logging()
    else:
        # if config exists, setup server logging
        set_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME, logserverurl)


def get_default_usage_logfilepath():
    """Returns default usage logging path. This path is automatically generated at module execution.

    Returns:
        str: Default usage logging path. This might not be the active path.
    """
    return PYREVIT_VERSION_APP_DIR


def get_current_usage_logpath():
    """Returns active usage logging path. This path might be the default, or set by user in user config.

    Returns:
        str: Active usage logging path.
    """
    return user_config.usagelogging.logfilepath


def get_current_usage_logfile():
    """
    Returns active usage logging full file path. This is the file that usage logs are being
    written to in current pyRevit session. Usage logging filenames are automatically generated
    at this module execution.

    Returns:
        str: Active usage logging full file path.
    """
    return get_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME)


def get_current_usage_serverurl():
    """
    Returns active usage logging server url. This is the server that usage logs are being
    sent to in current pyRevit session. Server url must be set by the user in config.

    Returns:
        str: Active usage logging server url.
    """
    return get_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME)


def is_active():
    """Returns status of usage logging system.

    Returns:
        bool: True if usage logging is active, False if not.
    """
    return get_pyrevit_env_var(USAGELOG_STATE_ISC_KEYNAME)
