#Select a filled region first and run this.
#this script will select all elements matching the type of the selected filled region
from Autodesk.Revit.DB import FilteredElementCollector
from Autodesk.Revit.DB import ElementId
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

CID = selection[0].Category.Id
TID = selection[0].GetTypeId()

cl = FilteredElementCollector(doc)
list = cl.OfCategoryId( CID ).WhereElementIsNotElementType().ToElements()

set = []

for r in list:
	if r.GetTypeId() == TID:
		set.append( r.Id )
		try:
			print('ID: {0}\t{1}OWNER VIEW: {2}'.format( r.Id,
														r.GetType().Name.ljust(20),
														doc.GetElement( r.OwnerViewId ).ViewName ))
		except:
			print('ID: {0}\t{1}'.format(	r.Id,
											r.GetType().Name.ljust(20) ))

uidoc.Selection.SetElementIds( List[ElementId]( set ) )