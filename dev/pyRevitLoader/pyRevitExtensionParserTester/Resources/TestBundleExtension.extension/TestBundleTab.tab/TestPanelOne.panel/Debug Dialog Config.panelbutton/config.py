from pyrevit.coreutils import logger
slogger = logger.get_logger(__commandname__)


if __shiftclick__:
    print('Shift-Clicked button')

if __forceddebugmode__:
    print('Ctrl-Clicked button')


slogger.debug('Debug message')
print('Try different Modifier keys with this button to check results.')
