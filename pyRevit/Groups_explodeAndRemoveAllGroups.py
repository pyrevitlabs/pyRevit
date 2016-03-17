'''
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
'''

__window__.Close()
import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Group, GroupType, Transaction, BuiltInParameter


uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction( doc, 'Explode and Purge All Groups' )
t.Start()

cl = FilteredElementCollector( doc )
grps = list( cl.OfClass( clr.GetClrType( Group )).ToElements() )

cl = FilteredElementCollector( doc )
grpTypes = list( cl.OfClass( clr.GetClrType( GroupType )).ToElements() )

attachedGrps = []

for g in grps:
	if g.LookupParameter('Attached to'):
		attachedGrps.append( g.GroupType )
	g.UngroupMembers()

for agt in attachedGrps:
	doc.Delete( agt.Id )



for gt in grpTypes:
	doc.Delete( gt.Id )

t.Commit()

