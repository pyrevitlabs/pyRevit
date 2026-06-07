# -*- coding: utf-8 -*-
"""Open the interactive IronPython shell as a modeless window."""
import clr
from System import AppDomain
from System.IO import Path, Directory

# The shell and its IronPython 3.4 engine ship in engines/IPY342, a sibling of whichever engine
# pyRevit is currently running. Locate it from the loaded pyRevitLoader assembly.
_engine_dir = None
for _asm in AppDomain.CurrentDomain.GetAssemblies():
    if _asm.GetName().Name == "pyRevitLoader":
        _engine_dir = Path.GetDirectoryName(_asm.Location)
        break

_engines_root = Directory.GetParent(_engine_dir).FullName
_shell_dll = Path.Combine(_engines_root, "IPY342", "pyRevitLabs.PyRevit.Shell.dll")

clr.AddReferenceToFileAndPath(_shell_dll)
from PyRevitLabs.PyRevit.Shell import Shell

Shell.Modeless(__revit__)
