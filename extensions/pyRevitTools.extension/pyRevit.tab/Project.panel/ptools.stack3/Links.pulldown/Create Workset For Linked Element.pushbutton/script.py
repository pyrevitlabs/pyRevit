"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
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

__doc__ = 'This tool will create a workset for the selected linked element base on its name. If the model is not workshared, it will be converted to workshared model.'

__window__.Close()
from Autodesk.Revit.DB import RevitLinkInstance, Transaction, Workset, ImportInstance, BuiltInParameter
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

linkedModelName = ''

if len(selection) > 0:
    for el in selection:
        if isinstance(el, RevitLinkInstance):
            linkedModelName = el.Name.Split(':')[0]
        elif isinstance(el, ImportInstance):
            linkedModelName = el.LookupParameter('Name').AsString()
        if linkedModelName:
            if not doc.IsWorkshared and doc.CanEnableWorksharing:
                doc.EnableWorksharing('Shared Levels and Grids', 'Workset1')
            with Transaction(doc, 'Create Workset for linked model') as t:
                t.Start()
                newWs = Workset.Create(doc, linkedModelName)
                worksetParam = el.Parameter[BuiltInParameter.ELEM_PARTITION_PARAM]
                worksetParam.Set(newWs.Id.IntegerValue)
                t.Commit()
else:
    TaskDialog.Show('pyrevit', 'At least one linked element must be selected.')
