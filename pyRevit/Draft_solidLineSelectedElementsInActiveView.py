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

__doc__ = 'Sets the element graphic override to Solid projection lines for the selected elements.'

__window__.Close()
from Autodesk.Revit.DB import Transaction, OverrideGraphicSettings, LinePatternElement

doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

with Transaction(doc,"Set Element to Solid Projection Line Pattern") as t:
	t.Start()
	for el in selection:
		if el.ViewSpecific:
			ogs = OverrideGraphicSettings()
			ogs.SetProjectionLinePatternId( LinePatternElement.GetSolidPatternId() )
			doc.ActiveView.SetElementOverrides( el.Id, ogs );
	t.Commit()