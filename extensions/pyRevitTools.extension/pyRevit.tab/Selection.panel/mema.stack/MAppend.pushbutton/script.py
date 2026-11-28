# -*- coding: utf-8 -*-
"""Add the selected elements to the selection memory of the active document."""

import selectionmemory

selectionmemory.write_memory(
    selectionmemory.read_memory() | selectionmemory.selected_ids()
)
