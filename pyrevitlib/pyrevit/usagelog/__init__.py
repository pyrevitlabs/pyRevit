import os.path as op

from pyrevit import EXEC_PARAMS
from pyrevit import PYREVIT_ADDON_NAME, PYREVIT_VERSION_APP_DIR, PYREVIT_FILE_PREFIX_STAMPED
from pyrevit.coreutils import is_blank
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.envvars import set_pyrevit_env_var

from pyrevit.userconfig import user_config


logger = get_logger(__name__)


# environment parameter names for communicating usage logging with
# the command executor and usage logger in c-sharp
USAGELOG_STATE_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_usagelogstateISC'
USAGELOG_FILEPATH_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_usagelogfileISC'
USAGELOG_SERVERURL_ISC_KEYNAME = PYREVIT_ADDON_NAME + '_usagelogserverISC'

# default file path and name for usage logging
FILE_LOG_FILENAME = '{}_usagelog.json'.format(PYREVIT_FILE_PREFIX_STAMPED)
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


def setup_usage_logfile():
    if not user_config.has_section('usagelogging'):
        user_config.add_section('usagelogging')

    usageloggingactive = user_config.usagelogging.get_option('active', default_value=False)
    set_pyrevit_env_var(USAGELOG_STATE_ISC_KEYNAME, usageloggingactive)

    logfilepath = user_config.usagelogging.get_option('logfilepath', default_value=USAGELOG_FILEPATH)
    logserverurl = user_config.usagelogging.get_option('logserverurl', default_value=USAGELOG_SERVERURL)

    if not logfilepath or is_blank(logfilepath):
        set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, USAGELOG_FILEPATH)
        if not op.exists(USAGELOG_FILEPATH):
            try:
                with open(USAGELOG_FILEPATH, 'w') as log_file:
                    log_file.write('[]')
            except Exception as write_err:
                logger.error('Usage logging is active but log file location is not accessible. | {}'.format(write_err))
                set_pyrevit_env_var(USAGELOG_STATE_ISC_KEYNAME, False)
    else:
        set_pyrevit_env_var(USAGELOG_FILEPATH_ISC_KEYNAME, logfilepath)

    if not logserverurl or is_blank(logserverurl):
        set_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME, USAGELOG_SERVERURL)
    else:
        set_pyrevit_env_var(USAGELOG_SERVERURL_ISC_KEYNAME, logserverurl)
