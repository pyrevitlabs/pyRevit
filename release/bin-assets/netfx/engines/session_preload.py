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

repo_path = op.dirname(op.dirname(op.dirname(op.dirname(__file__))))
sys.path.append(op.join(repo_path, 'pyrevitlib'))
sys.path.append(op.join(repo_path, 'site-packages'))

from pyrevit.loader import sessionmgr

sessionmgr.perform_preload()
