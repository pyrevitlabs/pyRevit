__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, ElementId, Transaction, BuiltInCategory
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView
roomtags = FilteredElementCollector( doc, curview.Id ).OfCategory(BuiltInCategory.OST_RoomTags).WhereElementIsNotElementType().ToElementIds()
rooms = FilteredElementCollector( doc, curview.Id ).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElementIds()

all = []

t = Transaction(doc, 'Isolate Room Tags') 
t.Start()

all.extend( rooms )
all.extend( roomtags )

curview.IsolateElementsTemporary( List[ElementId]( all ))

t.Commit()