from pyrevit.coreutils.logger import get_logger
logger = get_logger(__commandname__)

if __shiftclick__:
    print('Shift-Clicked button')

if __forceddebugmode__:
    print('Ctrl-Clicked button')


logger.debug('Debug message')
print('Try different Modifier keys with this button to check results.')
