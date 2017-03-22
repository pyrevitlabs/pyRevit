from pyrevit import EXEC_PARAMS
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


STANDARD_USAGE_LOG_PARAMS = ['time', 'username', 'revit', 'revitbuild', 'pyrevit', 'debug',
                             'alternate', 'commandname', 'result', 'source']


class CommandCustomResults:
    def __init__(self):
        pass

    def __getattr__(self, key):
        if not isinstance(key, str):
            logger.error('Key must be of type string (str).')
        else:
            return str(EXEC_PARAMS.result_dict[key])

    def __setattr__(self, key, value):
        if not isinstance(key, str) or not isinstance(value, str):
            logger.error('Both key and value must be of type string (str).')
        elif key in STANDARD_USAGE_LOG_PARAMS:
            logger.error('{} is a standard log param. Can not override this value.'.format(key))
        else:
            EXEC_PARAMS.result_dict.Add(key, value)
