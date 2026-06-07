# -*- coding: utf-8 -*-
"""Open the interactive IronPython shell as a modeless window."""
import sys
import clr
from System import AppDomain
from System.IO import Path
from System.Collections.Generic import List

# The shell DLL ships into the active engine folder (the IronPython fork pyRevit is configured to
# run), alongside the loaded pyRevitLoader. Loading it from there makes the shell use that engine.
_engine_dir = None
for _asm in AppDomain.CurrentDomain.GetAssemblies():
    if _asm.GetName().Name == "pyRevitLoader":
        _engine_dir = Path.GetDirectoryName(_asm.Location)
        break

clr.AddReferenceToFileAndPath(Path.Combine(_engine_dir, "pyRevitLabs.PyRevit.Shell.dll"))
from PyRevitLabs.PyRevit.Shell import Shell

# Forward this engine's sys.path so `from pyrevit import ...` resolves in the shell exactly as here.
_paths = List[str]()
for _p in sys.path:
    _paths.Add(_p)

Shell.Modeless(__revit__, _paths)
