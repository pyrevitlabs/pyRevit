"""Select previous element in selection memory.

Click +1
Shift+Click +10
"""

import iter_selection


iter_selection.iterate('-', 10 if __shiftclick__ else 1)
