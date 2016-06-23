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

__doc__ = 'Sums up the values of PERIMETER parameter on selected elements. Elements with no PERIMETER parameter will be skipped.'

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

total = 0.0
for el in selection:
    param = el.LookupParameter('Perimeter')
    if param:
        total += el.LookupParameter('Perimeter').AsDouble()
    else:
        print('Elemend with ID: {0} does not have Perimeter parameter.'.format(el.Id))
print("TOTAL PERIMETER OF ALL SELECTED ELEMENTS IS: {0}".format(total))
