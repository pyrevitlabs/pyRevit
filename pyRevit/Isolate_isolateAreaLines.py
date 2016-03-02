__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView
areaLines = FilteredElementCollector( doc, curview.Id ).OfCategory(BuiltInCategory.OST_AreaSchemeLines).WhereElementIsNotElementType().ToElementIds()

t = Transaction(doc, 'Isolate Area Boundaries') 
t.Start()

curview.IsolateElementsTemporary( areaLines )

t.Commit()