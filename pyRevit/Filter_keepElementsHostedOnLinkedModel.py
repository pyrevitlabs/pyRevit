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
from Autodesk.Revit.DB import ElementId, RevitLinkInstance
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

set = []
for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	host = el.Host
	if isinstance( host, RevitLinkInstance ):
		set.append( elId )

uidoc.Selection.SetElementIds( List[ElementId]( set ) )
uidoc.RefreshActiveView()