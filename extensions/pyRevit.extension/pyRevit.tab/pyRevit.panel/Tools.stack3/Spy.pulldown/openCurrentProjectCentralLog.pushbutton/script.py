"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Opens the central log for the current workshared project.'

__window__.Close()

import os, subprocess
import os.path as op

from Autodesk.Revit.DB import ModelPathUtils

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

if doc.GetWorksharingCentralModelPath():
    centralPath = ModelPathUtils.ConvertModelPathToUserVisiblePath(doc.GetWorksharingCentralModelPath())
    centralName = op.splitext(op.basename(centralPath))[0]
    slogFile = centralPath.replace('.rvt', '_backup\\{0}.slog'.format(centralName))
    pfFolder = os.getenv('ProgramFiles(x86)')
    nppExists = op.isfile(op.join(pfFolder, 'Notepad++\\Notepad++.EXE'))
    if nppExists:
        os.system('start notepad++ "{0}"'.format(slogFile))
    else:
        os.system('start notepad "{0}"'.format(slogFile))
else:
    print("Model is not work-shared.")
