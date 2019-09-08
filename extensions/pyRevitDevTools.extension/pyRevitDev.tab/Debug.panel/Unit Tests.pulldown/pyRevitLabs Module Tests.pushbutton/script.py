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
output.log_debug("""
Lorem Ipsum is simply dummy text of the printing and typesetting industry. 
Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, 
when an unknown printer took a galley of type and scrambled it to make a type 
specimen book. It has survived not only five centuries, but also the leap into 
electronic typesetting, remaining essentially unchanged. It was popularised in 
the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, 
and more recently with desktop publishing software like Aldus 
PageMaker including versions of Lorem Ipsum.

Contrary to popular belief, Lorem Ipsum is not simply random text. 
It has roots in a piece of classical Latin literature from 45 BC, making 
it over 2000 years old. Richard McClintock, a Latin professor at Hampden-Sydney 
College in Virginia, looked up one of the more obscure Latin words, 
consectetur, from a Lorem Ipsum passage, and going through the cites of the 
word in classical literature, discovered the undoubtable source. 
Lorem Ipsum comes from sections 1.10.32 and 1.10.33 of "de Finibus Bonorum 
et Malorum" (The Extremes of Good and Evil) by Cicero, written in 45 BC. 
This book is a treatise on the theory of ethics, very popular during the 
Renaissance. The first line of Lorem Ipsum, "Lorem ipsum dolor sit amet..", 
comes from a line in section 1.10.32.
""")
output.log_error('Example Error Message')

