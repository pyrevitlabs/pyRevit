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
FILE_LOG_FILENAME = '{}_{}_usagelog.json'.format(PYREVIT_FILE_PREFIX, get_session_uuid())
USAGELOG_FILEPATH = op.join(PYREVIT_VERSION_APP_DIR, FILE_LOG_FILENAME)

# default server url for usage logging
USAGELOG_SERVERURL = ''


class CommandCustomResults:
    # list of standard usage log record params provided by the c-sharp logger
    # scripts should not use these names
    RESERVED_NAMES = ['time', 'username', 'revit', 'revitbuild', 'sessionid', 'pyrevit', 'debug',
                       'alternate', 'commandname', 'result', 'source']

    def __init__(self):
        pass

    def __getattr__(self, key):
        return unicode(EXEC_PARAMS.result_dict[key])

    def __setattr__(self, key, value):
        if key in CommandCustomResults.RESERVED_NAMES:
            logger.error('{} is a standard log param. Can not override this value.'.format(key))
        else:
            EXEC_PARAMS.result_dict.Add(key, unicode(value))


def _disable_usage_logging():
    set_pyrevit_env_var(USAGELOG_STATE_ISC_KEYNAME, False)


def _disable_file_usage_logging():
    set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, '')


def _disable_server_usage_logging():
    set_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME, '')


def _setup_default_logfile():
    set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, USAGELOG_FILEPATH)
    if not op.exists(USAGELOG_FILEPATH):
        try:
            with open(USAGELOG_FILEPATH, 'w') as log_file:
                log_file.write('[]')
        except Exception as write_err:
            logger.error('Usage logging is active but log file location is not accessible. | {}'.format(write_err))
            _disable_usage_logging()


def setup_usage_logfile():
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


def get_current_usage_logfile():
    return get_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME)


def get_current_usage_serverurl():
    return get_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME)
