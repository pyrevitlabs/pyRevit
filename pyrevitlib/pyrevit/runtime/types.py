"""Provide access to classes and functionalty inside base loader module."""

from pyrevit.compat import IRONPY
from pyrevit.framework import clr
from pyrevit.runtime import RUNTIME_ASSM

#pylint: disable=import-error,invalid-name,broad-except,wildcard-import
# import base classes module
if IRONPY:
    clr.AddReference(RUNTIME_ASSM)
else:
    clr.AddReference(RUNTIME_ASSM.Location)

from PyRevitLabs.PyRevit.Runtime import *
