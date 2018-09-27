import clr
from pyrevit.loader.addin import engines
from pyrevit.labs import NLog

from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms  
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


nlogger = NLog.LogManager.GetLogger(__name__ + 'NLOG')
nlogger.Info('sdfsdfdsf')
nlogger.Debug('sdfsdfdsf')
nlogger.Warn('sdfsdfdsf')
nlogger.Fatal('sdfsdfdsf')

logger.info('sfdfsdf')
logger.debug('sfdfsdf')


print(engines.get_engine(277))

print(engines.get_engine(273))

print(engines.get_latest_engine())

for eng in engines.get_engines():
    print(eng)


output.window.activityBar.ConsoleLogInfo('sdfsdfd')
output.window.activityBar.IsActive = True
