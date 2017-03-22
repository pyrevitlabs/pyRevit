import os.path as op

from pyrevit import EXEC_PARAMS
from pyrevit import PYREVIT_ADDON_NAME, PYREVIT_VERSION_APP_DIR, PYREVIT_FILE_PREFIX_STAMPED
from pyrevit.coreutils import is_blank
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.envvars import set_pyrevit_env_var


logger = get_logger(__name__)


FILELOG_ISC_NAME = PYREVIT_ADDON_NAME + '_usagelogfileISC'
SERVERLOG_ISC_NAME = PYREVIT_ADDON_NAME + '_usagelogserverISC'

FILE_LOG_FILENAME = '{}_usage.log'.format(PYREVIT_FILE_PREFIX_STAMPED)
FILE_LOG_FILEPATH = op.join(PYREVIT_VERSION_APP_DIR, FILE_LOG_FILENAME)


STANDARD_USAGE_LOG_PARAMS = ['time', 'username', 'revit', 'revitbuild', 'sessionid', 'pyrevit', 'debug',
                             'alternate', 'commandname', 'result', 'source']


class CommandCustomResults:
    def __init__(self):
        pass

    def __getattr__(self, key):
        if not isinstance(key, unicode):
            logger.error('Key must be of type string (str).')
        else:
            return unicode(EXEC_PARAMS.result_dict[key])

    def __setattr__(self, key, value):
        if not isinstance(key, unicode) or not isinstance(value, unicode):
            logger.error('Both key and value must be of type string (str).')
        elif key in STANDARD_USAGE_LOG_PARAMS:
            logger.error('{} is a standard log param. Can not override this value.'.format(key))
        else:
            EXEC_PARAMS.result_dict.Add(key, value)


def setup_usage_logfile(logfilepath=None, logserverurl=None):
    if not logfilepath or is_blank(logfilepath):
        set_pyrevit_env_var(FILELOG_ISC_NAME, FILE_LOG_FILEPATH)
    else:
        set_pyrevit_env_var(FILELOG_ISC_NAME, logfilepath)

    if not logserverurl or is_blank(logserverurl):
        set_pyrevit_env_var(SERVERLOG_ISC_NAME, '')
    else:
        set_pyrevit_env_var(SERVERLOG_ISC_NAME, logserverurl)
