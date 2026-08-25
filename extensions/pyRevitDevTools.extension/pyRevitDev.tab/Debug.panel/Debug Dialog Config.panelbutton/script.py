"""This is the panel pushbutton (Could be used for panel config)."""

from pyrevit import script
logger = script.get_logger()


# panelbutton should discard the __context__
# they should always be active


if __shiftclick__:
    print('Shift-Clicked button')

if __forceddebugmode__:
    print('Ctrl-Clicked button')


logger.debug('Debug message')
print('Try different Modifier keys with this button to check results.')
