# -*- coding: utf-8 -*-
"""Select the elements stored in the selection memory of the active document."""

from pyrevit import revit

import selectionmemory

revit.get_selection().set_to(selectionmemory.require_memory_element_ids())
