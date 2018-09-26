import logging

from pyrevit import HOME_DIR
from pyrevit.framework import clr

from pyrevit.coreutils import logger

# try loading pyrevitlabs
clr.AddReference('Nett')
clr.AddReference('Nlog')
clr.AddReference('pyRevitLabs.Common')
clr.AddReference('pyRevitLabs.CommonCLI')
clr.AddReference('pyRevitLabs.Language')
clr.AddReference('pyRevitLabs.TargetApps.Revit')
import Nett
import NLog
from pyRevitLabs import Common
from pyRevitLabs import CommonCLI
from pyRevitLabs import Language
from pyRevitLabs import TargetApps


mlogger = logger.get_logger(__name__)


# setup logger
class PyRevitOutputTarget(NLog.Targets.TargetWithLayout):
    def Write(self, asyncLogEvent):
        try:
            event = asyncLogEvent.LogEvent
            level = self.convert_level(event.Level)
            if mlogger.is_enabled_for(level):
                print(self.Layout.Render(event))
        except Exception as e:
            print(e)
    
    def convert_level(self, nlog_level):
        if nlog_level == NLog.LogLevel.Fatal:
            return logging.CRITICAL
        elif nlog_level == NLog.LogLevel.Error:
            return logging.ERROR
        elif nlog_level == NLog.LogLevel.Info:
            return logging.INFO
        elif nlog_level == NLog.LogLevel.Debug:
            return logging.DEBUG
        elif nlog_level == NLog.LogLevel.Off:
            return logging.DEBUG
        elif nlog_level == NLog.LogLevel.Trace:
            return logging.DEBUG
        elif nlog_level == NLog.LogLevel.Warn:
            return logging.WARNING


config = NLog.Config.LoggingConfiguration()
target = PyRevitOutputTarget()
target.Name = __name__
target.Layout = "${level:uppercase=true}: [${logger}] ${message}"
config.AddTarget(target)
config.AddRuleForAllLevels(target)
NLog.LogManager.Configuration = config

for rule in NLog.LogManager.Configuration.LoggingRules:
    rule.EnableLoggingForLevel(NLog.LogLevel.Info)
    rule.EnableLoggingForLevel(NLog.LogLevel.Debug)

NLog.LogManager.GetLogger(__name__)
