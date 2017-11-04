"""This is the tooltip content"""

from pyrevit.coreutils import logger
slogger = logger.get_logger(__commandname__)


__context__ = 'zerodoc'
__helpurl__ = "https://www.youtube.com/channel/UC-0THIvKRd6n7T2a5aKYaGg"


if __shiftclick__:
    print('Shift-Clicked button')

if __forceddebugmode__:
    print('Ctrl-Clicked button')


slogger.debug('Debug message')
print('Try different Modifier keys with this button to check results.')
