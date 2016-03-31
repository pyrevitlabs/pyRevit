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

# from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

from Autodesk.Revit.DB import CurveElement

def isline( line ):
	return isinstance( line, CurveElement )

for elId in uidoc.Selection.GetElementIds():
	# if 'Lines' == el.Category.Name:
	if isline(el):
		el = doc.GetElement( elId )
		# print( el.GeometryCurve.EndPoint[0][2] )
		# print( el.GeometryCurve.EndPoint[1][2] )
		print( el.GeometryCurve.GetEndPoint(0) )
		print( el.GeometryCurve.GetEndPoint(1) )
	else:
		print('Elemend with ID: {0} is a not a line.'.format( el.Id ))