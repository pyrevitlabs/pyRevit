# -*- coding: utf-8 -*-
#pylint: disable=C0103,W1401,E0401,E0602
"""Post-load entry point invoked by the C# session orchestrator.

Finalizes the session after the C# loader has built the UI. See
pyrevit.loader.sessionmgr.perform_postload().
"""

import sys

sys.setrecursionlimit(1000)

from pyrevit.loader import sessionmgr

sessionmgr.perform_postload()
