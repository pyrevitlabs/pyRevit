__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView
doors = FilteredElementCollector( doc, curview.Id ).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsNotElementType().ToElementIds()

t = Transaction(doc, 'Isolate Doors') 
t.Start()

curview.IsolateElementsTemporary( doors )

t.Commit()