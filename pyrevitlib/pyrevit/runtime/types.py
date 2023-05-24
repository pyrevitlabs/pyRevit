"""Provide access to classes and functionalty inside base loader module."""

from pyrevit import EXEC_PARAMS
from pyrevit.compat import PY3
from pyrevit.framework import clr
from pyrevit.runtime import RUNTIME_ASSM

#pylint: disable=import-error,invalid-name,broad-except,wildcard-import
if not EXEC_PARAMS.doc_mode:
    # import base classes module
    if PY3:
        clr.AddReference(RUNTIME_ASSM.Location)
    else:
        clr.AddReference(RUNTIME_ASSM)

    from PyRevitLabs.PyRevit.Runtime import *
else:
    # define the values for docs
    ScriptConsoleManager = None
    EventTelemetry = None
    EventType = None
    EventHooks = None
