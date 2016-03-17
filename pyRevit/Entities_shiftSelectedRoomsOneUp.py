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