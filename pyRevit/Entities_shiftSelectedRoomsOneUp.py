from Autodesk.Revit.DB import Transaction
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction(doc, 'Shift Rooms') 
t.Start()

selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]
roomList = sorted( selection, key = lambda room: room.LookupParameter('Number').AsString()[1:4] )
roomList.reverse()

for el in roomList:
	# roomNumber = int( el.LookupParameter('Number').AsString()[1:4] )
	# roomSubCat = el.LookupParameter('Number').AsString()[4:]
	# roomCat = el.LookupParameter('Number').AsString()[0:1]
	# newNumber = str( roomCat + '{0:03}'.format( roomNumber + 1 ) ) + roomSubCat
	roomNumber = int( el.LookupParameter('Number').AsString() )
	newNumber = str( roomNumber + 1 )
	# print str(roomCat) + str(roomNumber) + '\t -> \t' + newNumber
	print str(roomNumber) + '\t -> \t' + newNumber
	el.LookupParameter('Number').Set( newNumber  )

t.Commit()