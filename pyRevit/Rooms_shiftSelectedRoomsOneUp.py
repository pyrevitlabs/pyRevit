from Autodesk.Revit.DB import Transaction
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction(doc, 'Shift Rooms') 
t.Start()

roomList = sorted( uidoc.Selection.Elements, key = lambda room: room.ParametersMap['Number'].AsString()[1:4] )
roomList.reverse()

for el in roomList:					# uidoc.Selection.Elements.ReverseIterator()
	param = el.ParametersMap
	roomNumber = int( param['Number'].AsString()[1:4] )
	roomSubCat = param['Number'].AsString()[4:]
	roomCat = param['Number'].AsString()[0:1]
	newNumber = str( roomCat + '{0:03}'.format( roomNumber + 1 ) ) + roomSubCat
	print str(roomCat) + str(roomNumber) + '\t -> \t' + newNumber
	param['Number'].Set( newNumber  )

t.Commit()