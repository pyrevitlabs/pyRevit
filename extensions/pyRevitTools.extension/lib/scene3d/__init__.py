# -*- coding: utf-8 -*-
"""Shared building blocks for WebGL scene previews in the output window.

Used by the buttons that draw model geometry in a WebView2 output page
(Diagnose Invisibility, Section Box Navigator): geometry tessellation with
vertex budgets and packed JSON (``meshing``), the page/Python message channel
(``bridge``) and the asset loader for the shared page script (``gl.js``).
"""

import io
import os

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))


def read_asset(name):
    """Return the text of a file shipped next to this package, such as ``gl.js``."""
    with io.open(os.path.join(_LIB_DIR, name), encoding="utf-8") as asset:
        return asset.read()
