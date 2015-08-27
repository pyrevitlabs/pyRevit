# from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	# print( el.GeometryCurve.EndPoint[0][2] )
	# print( el.GeometryCurve.EndPoint[1][2] )
	print( el.GeometryCurve.GetEndPoint(0) )
	print( el.GeometryCurve.GetEndPoint(1) )