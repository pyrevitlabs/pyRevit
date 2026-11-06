# -*- coding: utf-8 -*-
"""Legend view drawing shared by pyRevitTools commands.

Filter Legend is the reference implementation: its layout (swatch
column, measured text rows, auto-fitted columns) is what every tool
drawing a color legend reuses, so improvements land here once.

  * ``legend.drawing`` -- low-level primitives (text notes, swatches,
    measuring, clearing a legend's own elements).
  * ``legend.table`` -- the header-plus-rows table built from them.
"""
