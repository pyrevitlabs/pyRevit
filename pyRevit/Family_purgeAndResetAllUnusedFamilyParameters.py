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

__doc__ = 'This script removes all custom parameters that has not been used in dimensions as labels and also resets the value for the other parameters to zero or null.'

import clr
from Autodesk.Revit.DB import Transaction, ElementId, StorageType, FilteredElementCollector, Dimension, FamilyParameter
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

if doc.IsFamilyDocument:
    params = doc.FamilyManager.GetParameters()
    dims = FilteredElementCollector(doc).OfClass(Dimension).WhereElementIsNotElementType()

    labelParams = set()
    for d in dims:
        try:
            if isinstance(d.FamilyLabel, FamilyParameter):
                labelParams.add(d.FamilyLabel.Id.IntegerValue)
        except:
            continue

    print('STARTING CLEANUP...')
    t = Transaction(doc, 'Remove all family parameters')
    t.Start()

    for param in params:
        try:
            print('\nREMOVING FAMILY PARAMETER:\nID: {0}\tNAME: {1}'.format(param.Id, param.Definition.Name))
            if param.Id.IntegerValue not in labelParams:
                doc.FamilyManager.RemoveParameter(param)
                print('REMOVED.')
            else:
                print('NOT REMOVED. PARAMETER IS BEING USED AS A LABEL.')
        except:
            print('-- CAN NOT DELETE --')
            try:
                if param.CanAssignFormula:
                    doc.FamilyManager.SetFormula(param, None)
                if param.StorageType == StorageType.Integer or param.StorageType == StorageType.Double:
                    doc.FamilyManager.Set(param, 0)
                    print('-- PARAMETER VALUE SET TO INTEGER 0')
                elif param.StorageType == StorageType.String:
                    doc.FamilyManager.Set(param, '')
                    print('-- PARAMETER VALUE SET TO EMPTY STRING.')
                else:
                    print('-- PARAMETER TYPE IS UNKNOWN. CAN NOT RESET VALUE.')
            except Exception as e:
                print e
                continue
            continue
    print('\n\nALL DONE.....................................')
    t.Commit()
else:
    __window__.Close()
    TaskDialog.Show('pyRevit', 'This script works only on an active family editor.')
