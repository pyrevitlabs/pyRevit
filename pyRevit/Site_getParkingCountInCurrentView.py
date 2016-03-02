from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView
areaLines = FilteredElementCollector( doc, curview.Id ).OfCategory(BuiltInCategory.OST_Parking).WhereElementIsNotElementType().ToElementIds()

print('PARKING COUNT: {0}'.format( len( list( areaLines ))))