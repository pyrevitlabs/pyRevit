import os.path as op

from pyrevit import EXEC_PARAMS
from pyrevit import PYREVIT_ADDON_NAME, PYREVIT_VERSION_APP_DIR, PYREVIT_FILE_PREFIX_STAMPED
from pyrevit.coreutils import is_blank
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.envvars import set_pyrevit_env_var

from pyrevit.userconfig import user_config


logger = get_logger(__name__)


USAGELOGSTATE_ISC_NAME = PYREVIT_ADDON_NAME + '_usagelogstateISC'
FILELOG_ISC_NAME = PYREVIT_ADDON_NAME + '_usagelogfileISC'
SERVERLOG_ISC_NAME = PYREVIT_ADDON_NAME + '_usagelogserverISC'

FILE_LOG_FILENAME = '{}_usagelog.json'.format(PYREVIT_FILE_PREFIX_STAMPED)
FILE_LOG_FILEPATH = op.join(PYREVIT_VERSION_APP_DIR, FILE_LOG_FILENAME)


STANDARD_USAGE_LOG_PARAMS = ['time', 'username', 'revit', 'revitbuild', 'sessionid', 'pyrevit', 'debug',
                             'alternate', 'commandname', 'result', 'source']


class CommandCustomResults:
    def __init__(self):
        pass

    def __getattr__(self, key):
        return unicode(EXEC_PARAMS.result_dict[key])

    def __setattr__(self, key, value):
        if key in STANDARD_USAGE_LOG_PARAMS:
            logger.error('{} is a standard log param. Can not override this value.'.format(key))
        else:
            EXEC_PARAMS.result_dict.Add(key, unicode(value))


def setup_usage_logfile():
    if not user_config.has_section('usagelogging'):
        user_config.add_section('usagelogging')
    
    usageloggingactive = user_config.usagelogging.get_option('active', default_value=False)
    set_pyrevit_env_var(USAGELOGSTATE_ISC_NAME, usageloggingactive)

    logfilepath = user_config.usagelogging.get_option('logfilepath', default_value='')
    logserverurl = user_config.usagelogging.get_option('logserverurl', default_value='')

    if not logfilepath or is_blank(logfilepath):
        set_pyrevit_env_var(FILELOG_ISC_NAME, FILE_LOG_FILEPATH)
        if not op.exists(FILE_LOG_FILEPATH):
            try:
                with open(FILE_LOG_FILEPATH, 'w') as log_file:
                    log_file.write('[]')
            except Exception as write_err:
                logger.error('Usage logging is active but log file location is not accessible. | {}'.format(write_err))
                set_pyrevit_env_var(USAGELOGSTATE_ISC_NAME, False)
    else:
        set_pyrevit_env_var(FILELOG_ISC_NAME, logfilepath)

    if not logserverurl or is_blank(logserverurl):
        set_pyrevit_env_var(SERVERLOG_ISC_NAME, '')
    else:
        set_pyrevit_env_var(SERVERLOG_ISC_NAME, logserverurl)
