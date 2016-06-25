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

__doc__ = 'Find all constraints attached to the selected element.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


def listconstraints(selelement):
    print('THIS OBJECT ID: {0}'.format(selelement.Id))
    clconst = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Constraints).WhereElementIsNotElementType()
    constlst = set()
    for cnst in clconst:
        refs = [(x.ElementId, x) for x in cnst.References]
        elids = [x[0] for x in refs]
        if selelement.Id in elids:
            constlst.add(cnst)
            print("CONST TYPE: {0} # OF REFs: {1} CONST ID: {2}".format(cnst.GetType().Name.ljust(28),
                                                                        str(cnst.References.Size).ljust(24), cnst.Id))
            for t in refs:
                ref = t[1]
                elid = t[0]
                if elid == selelement.Id:
                    elid = str(elid) + ' (this)'
                print("     {0} LINKED OBJ CATEGORY: {1} ID: {2}".format(ref.ElementReferenceType.ToString().ljust(35),
                                                                         doc.GetElement(
                                                                             ref.ElementId).Category.Name.ljust(20),
                                                                         elid))
            print('\n')
    print('\n')


for elId in uidoc.Selection.GetElementIds():
    el = doc.GetElement(elId)
    listconstraints(el)
