# -*- coding: utf-8 -*-
#pylint: disable=C0103,W1401,E0401,E0602
"""Post-load entry point invoked by the C# session orchestrator.

Sets up the search paths so the pyrevit module is importable, then finalizes the
session after the C# loader has built the UI. See
pyrevit.loader.sessionmgr.perform_postload().
"""

import sys
import os.path as op

sys.setrecursionlimit(1000)

repo_path = op.dirname(op.dirname(op.dirname(op.dirname(__file__))))
sys.path.append(op.join(repo_path, 'pyrevitlib'))
sys.path.append(op.join(repo_path, 'site-packages'))

from pyrevit.loader import sessionmgr

sessionmgr.perform_postload()
