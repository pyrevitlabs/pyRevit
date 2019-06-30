import os.path as op
import logging
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import USER_SYS_TEMP
from pyrevit import coreutils
from pyrevit import script


slogger = script.get_logger()


# create own logger
LOG_REC_FORMAT_FILE = "%(asctime)s %(levelname)s: [%(name)s] %(message)s"
LOG_FILEPATH = op.join(USER_SYS_TEMP, 'indeplog.log')
file_hndlr = logging.FileHandler(LOG_FILEPATH, mode='a')
file_formatter = logging.Formatter(LOG_REC_FORMAT_FILE)
file_hndlr.setFormatter(file_formatter)
logger = logging.getLogger('MyIndependentLogger')    # type: LoggerWrapper
logger.addHandler(file_hndlr)

slogger.info('logget type: %s', type(slogger))
slogger.critical('testing CRITICAL')
slogger.error('testing ERROR')
slogger.warning('testing WARNING')
slogger.info('testing INFO')
slogger.debug('testing DEBUG')


logger.info('logget type: %s', type(logger))
logger.critical('testing CRITICAL')
logger.error('testing ERROR')
logger.warning('testing WARNING')
logger.info('testing INFO')
logger.debug('testing DEBUG')


coreutils.show_entry_in_explorer(LOG_FILEPATH)

del logger