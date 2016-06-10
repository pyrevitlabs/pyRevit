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

__doc__ = 'Lists all revision clouds in this model that have been placed on a view and not on sheet.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ViewSheet
doc = __revit__.ActiveUIDocument.Document


cl = FilteredElementCollector(doc)
revs = cl.OfCategory(BuiltInCategory.OST_RevisionClouds).WhereElementIsNotElementType()

for rev in revs:
	parent = doc.GetElement( rev.OwnerViewId )
	if isinstance(parent, ViewSheet):
		continue
	else:
		print('REV#: {0}\t\tID: {2}\t\tON VIEW: {1}'.format( doc.GetElement( rev.RevisionId ).RevisionNumber, parent.ViewName, rev.Id ))

print('\nSEARCH COMPLETED.')