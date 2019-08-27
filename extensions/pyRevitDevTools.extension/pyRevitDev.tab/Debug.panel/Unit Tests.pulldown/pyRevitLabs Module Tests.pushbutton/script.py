import clr
from pyrevit.labs import NLog

from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms  
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


print('Testing NLog logger from pyRevitLabs modules')
nlogger = NLog.LogManager.GetLogger(__name__ + 'NLOG')
nlogger.Info('Info Message')
nlogger.Warn('Warning Message')
nlogger.Error('Error Message')
nlogger.Fatal('Fatal|Critical Message')
nlogger.Debug('Debug Message')

print('Testing pyrevit logger compatibility with NLog')
logger.info('info Message')
logger.success('success Message')
logger.warning('Warning Message')
logger.error('error Message')
logger.critical('critical Message')
logger.debug('debug Message')
logger.deprecate('deprecate Message')

print('Testing pyRevitLabs CommonWPF ActivityBar interface...')
output.log_error('sdfdsfsdffds')

