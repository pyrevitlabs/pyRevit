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

__doc__ = 'This script removes all instances of the selected element Family and tries to convert the family into face host based. Only families of CommunicationDevices, DataDevices, DuctTerminal, ElectricalEquipment, ElectricalFixtures, FireAlarmDevices, LightingDevices, LightingFixtures, MechanicalEquipment, NurseCallDevices, PlumbingFixtures, SecurityDevices, Sprinklers, TelephoneDevices can be converted.'

import clr
from Autodesk.Revit.DB import Transaction, ElementId, FilteredElementCollector, FamilyInstanceFilter, FamilyUtils
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


def deleteallinstances(family):
    matchlist = []
    try:
        symbolidset = family.GetFamilySymbolIds()
        for symid in symbolidset:
            cl = FilteredElementCollector(doc).WherePasses(FamilyInstanceFilter(doc, symid)).ToElements()
            for faminstance in cl:
                matchlist.append(faminstance.Id)
    except:
        raise Exception

    for elid in matchlist:
        try:
            doc.Delete(elid)
        except:
            raise Exception


res = TaskDialog.Show('pyrevit',
                      'All instances of the selected families will be removed for this conversion.'
                      'Are you ready to proceed?',
                      TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.Cancel)

if res == TaskDialogResult.Yes:
    for elid in uidoc.Selection.GetElementIds():
        el = doc.GetElement(elid)
        fam = el.Symbol.Family
        famid = el.Symbol.Family.Id
        print('\nStarting conversion for family: {0}'.format(fam.Name))
        try:
            with Transaction(doc, 'Convert to Face Host Based') as t:
                t.Start()
                deleteallinstances(fam)
                FamilyUtils.ConvertFamilyToFaceHostBased(doc, famid)
                t.Commit()
            print('Conversion Successful.')
        except Exception as e:
            print('Conversion failed for family: {0}'.format(fam.Name))
            print('Exception Description:\n{0}'.format(e))
else:
    print('----------- Conversion Cancelled --------------')
