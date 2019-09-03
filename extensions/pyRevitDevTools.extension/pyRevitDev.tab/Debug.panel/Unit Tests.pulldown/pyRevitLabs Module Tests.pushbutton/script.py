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
nlogger.Info('Info message')
nlogger.Warn('Warning message')
nlogger.Error('Error message')
nlogger.Fatal('Fatal|Critical message')
nlogger.Debug('Debug message')

print('Testing pyrevit logger compatibility with NLog')
logger.debug('debug message')
logger.info('info message :OK_hand:')
logger.warning('Warning message')
logger.error('error message')
logger.critical('critical message')
logger.success('success message')
logger.deprecate('deprecate message')

print('Testing pyRevitLabs CommonWPF ActivityBar interface...')
output.log_error('sdfdsfsdffds')

