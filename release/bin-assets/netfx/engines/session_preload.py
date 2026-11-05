# -*- coding: utf-8 -*-
# pylint: disable=C0103,W1401,E0401,E0602
"""Pre-load entry point invoked by the C# session orchestrator.

Runs the pre-load session setup after the C# orchestrator has initialized the
runtime. See pyrevit.loader.sessionmgr.perform_preload().

The attachment cache is cleared before sessionmgr is imported: its import chain
(pyrevit.runtime) makes the session's first attachment lookup, so clearing first
lets a reload pick up a re-attached clone while the rest of the load reuses that
single lookup.
"""

import sys

# Defense-in-depth: a runaway circular import in pyRevit or any user extension
# must raise a catchable RecursionError rather than overflow the native stack
# and crash Revit.
sys.setrecursionlimit(1000)

from pyrevit.labs import PyRevit

PyRevit.PyRevitAttachments.ClearAttachmentCache()

from pyrevit.loader import sessionmgr

sessionmgr.perform_preload()
