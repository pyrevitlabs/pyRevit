# -*- coding: utf-8 -*-
"""Select the next element of the selection memory."""

from pyrevit import EXEC_PARAMS

import selectionmemory

selectionmemory.step_through_memory(1, 10 if EXEC_PARAMS.config_mode else 1)
