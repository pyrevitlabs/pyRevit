__doc__ = 'Select next element in saved selection\nClick +1\nShift+Click +10'
__title__ = 'Next'

# noinspection PyUnresolvedReferences
import iter_selection

step_size = 1
if __shiftclick__:
    step_size = 10

mode = '+'

result = iter_selection.iterate( mode, step_size )

