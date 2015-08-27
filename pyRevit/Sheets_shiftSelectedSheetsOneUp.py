from Autodesk.Revit.DB import Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction(doc, 'Shift Sheets') 
t.Start()

shift = 1

selectedSheets = []
for elId in uidoc.Selection.GetElementIds():
	selectedSheets.append( doc.GetElement( elId ))

sheetList = sorted( selectedSheets, key = lambda sheet: int(sheet.ParametersMap['Sheet Number'].AsString()[1:] ))

if shift >=0:
	sheetList.reverse()

for el in sheetList:	# uidoc.Selection.Elements.ReverseIterator()
	sheetNumber = el.LookupParameter('Sheet Number').AsString()
	sCat = sheetNumber[0:1]
	sNum = int( sheetNumber[1:] )
	newName = str( sCat + '{0:03}'.format( sNum + shift ) )
	print sheetNumber + '\t -> \t' + newName
	el.LookupParameter('Sheet Number').Set( newName )

t.Commit()

# __window__.Close()