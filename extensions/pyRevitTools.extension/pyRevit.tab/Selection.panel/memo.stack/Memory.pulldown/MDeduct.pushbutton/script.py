# -*- coding: utf-8 -*-
"""Remove the selected elements from the selection memory of the active document."""

import selectionmemory

selectionmemory.write_memory(
    selectionmemory.read_memory() - selectionmemory.selected_ids()
)
