"""Select previous element in selection memory.

Click +1
Shift+Click +10
"""

import iter_selection
from pyrevit import EXEC_PARAMS

iter_selection.iterate('-', 10 if EXEC_PARAMS.config_mode else 1)
