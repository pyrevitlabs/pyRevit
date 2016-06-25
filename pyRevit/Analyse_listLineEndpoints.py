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

# from Autodesk.Revit.DB import *

__doc__ = 'Lists XYZ coordinates of selected line endpoints.'

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

from Autodesk.Revit.DB import ModelArc, ModelLine, DetailArc, DetailLine


def isline(line):
    if isinstance(line, ModelArc) or isinstance(line, ModelLine) or isinstance(line, DetailArc) or isinstance(line, DetailLine):
        return True
    return False


for elId in uidoc.Selection.GetElementIds():
    el = doc.GetElement(elId)
    if isline(el):
        print('Line ID: {0}'.format(el.Id))
        print('Start:\t {0}'.format(el.GeometryCurve.GetEndPoint(0)))
        print('End:\t {0}\n'.format(el.GeometryCurve.GetEndPoint(1)))
    else:
        print('Elemend with ID: {0} is a not a line.\n'.format(el.Id))
