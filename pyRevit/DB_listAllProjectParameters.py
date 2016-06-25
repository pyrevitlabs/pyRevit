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

__doc__ = 'Lists all project parameters in this model.'

from Autodesk.Revit.DB import InstanceBinding, TypeBinding

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

pm = doc.ParameterBindings
it = pm.ForwardIterator()
it.Reset()
while it.MoveNext():
    p = it.Key
    b = pm[p]
    if isinstance(b, InstanceBinding):
        bind = 'Instance'
    elif isinstance(b, TypeBinding):
        bind = 'Type'
    else:
        bind = 'Uknown'

    print('PARAM: {0:<10} UNIT: {1:<10} TYPE: {2:<10} GROUP: {3:<20} BINDING: {4}\nAPPLIED TO: {5}\n'.format(
        p.Name,
        str(p.UnitType),
        str(p.ParameterType),
        str(p.ParameterGroup),
        bind,
        [c.Name for c in b.Categories]
    ))
