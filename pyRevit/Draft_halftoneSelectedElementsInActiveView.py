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

__doc__ = 'Sets element graphic override to halftone on the selected elements. If any of the elements is a group, the script will apply the override to all its members.'

__window__.Close()
from Autodesk.Revit.DB import Transaction, OverrideGraphicSettings, Group

doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

with Transaction(doc, 'Halftone Elements in View') as t:
    t.Start()
    for el in selection:
        if isinstance(el, Group):
            for mem in el.GetMemberIds():
                selection.append(doc.GetElement(mem))
        ogs = OverrideGraphicSettings()
        ogs.SetHalftone(True)
        # ogs.SetProjectionFillPatternVisible(False)
        doc.ActiveView.SetElementOverrides(el.Id, ogs);
    t.Commit()
