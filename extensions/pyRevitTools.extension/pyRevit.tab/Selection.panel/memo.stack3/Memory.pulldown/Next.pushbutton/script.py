"""Select next element in selection memory

Click +1
Shift+Click +10
"""

# noinspection PyUnresolvedReferences
import iter_selection

step_size = 1
if __shiftclick__:
    step_size = 10

mode = '+'

result = iter_selection.iterate( mode, step_size )
