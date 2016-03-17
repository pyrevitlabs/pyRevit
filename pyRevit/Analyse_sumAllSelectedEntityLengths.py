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

from Autodesk.Revit.DB import CurveElement

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

def isline( line ):
	return isinstance( line, CurveElement )

total = 0.0
lines = []

print("PROCESSING TOTAL OF {0} OBJECTS:\n\n".format( len( selection )))

for i, el in enumerate(selection):
	if isline( el ):
		lines.append( el )
	total += el.LookupParameter('Length').AsDouble()
print("TOTAL LENGTH OF ALL SELECTED ELEMENTS IS: {0}\n\n\n".format( total ))

#group lines per line style
linestyles = {}
for l in lines:
	if l.LineStyle.Name in linestyles:
		linestyles[ l.LineStyle.Name ].append( l )
	else:
		linestyles[ l.LineStyle.Name ] = [ l ]

for k in sorted( linestyles.keys() ):
	linestyletotal = 0.0
	for l in linestyles[k]:
		linestyletotal += l.LookupParameter('Length').AsDouble()
	print("- LINES OF STYLE: {0} -\nTOTAL LENGTH : {1}\n\n".format( k, linestyletotal ))
