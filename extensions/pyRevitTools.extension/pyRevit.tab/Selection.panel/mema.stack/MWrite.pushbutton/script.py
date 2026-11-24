# -*- coding: utf-8 -*-
"""Replace the selection memory of the active document with the selected elements."""

import selectionmemory

selectionmemory.write_memory(selectionmemory.selected_ids())
