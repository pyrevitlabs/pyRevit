from Autodesk.Revit.DB import CurveElement
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

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
	print("- LINES OF STYLE {0} -\nTOTAL LENGTH : {1}\n\n".format( k, linestyletotal ))
