# -*- coding: utf-8 -*-
#pylint: disable=C0103,W1401,E0401,E0602
"""Pre-load entry point invoked by the C# session orchestrator.

Sets up the search paths so the pyrevit module is importable, then runs the
pre-load session setup. See pyrevit.loader.sessionmgr.perform_preload().
"""

import sys
import os.path as op

# Defense-in-depth: a runaway circular import in pyRevit or any user extension
# must raise a catchable RecursionError rather than overflow the native stack
# and crash Revit.
sys.setrecursionlimit(1000)

# Discover the pyRevit root by walking up from this file's location until the
# pyrevitlib directory is found.  This handles both installed layouts
# (bin/engines/<script>) and build layouts (bin/netcore/engines/<script>).
def _find_pyrevit_root(start):
    current = op.abspath(start)
    while True:
        if op.isdir(op.join(current, 'pyrevitlib')):
            return current
        parent = op.dirname(current)
        if parent == current:
            return None
        current = parent

_root = _find_pyrevit_root(op.dirname(op.abspath(__file__)))
if _root:
    _pyrevitlib = op.join(_root, 'pyrevitlib')
    _site_packages = op.join(_root, 'site-packages')
    if _pyrevitlib not in sys.path:
        sys.path.insert(0, _pyrevitlib)
    if op.isdir(_site_packages) and _site_packages not in sys.path:
        sys.path.insert(0, _site_packages)
else:
    raise RuntimeError(
        "pyRevit root not found: could not locate 'pyrevitlib' by walking up from '{}'".format(__file__)
    )

from pyrevit.loader import sessionmgr

sessionmgr.perform_preload()
