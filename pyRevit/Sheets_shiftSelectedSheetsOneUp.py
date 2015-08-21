from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

t = Transaction(doc, 'Shift Sheets') 
t.Start()

shift = 1

sheetList = sorted( uidoc.Selection.Elements, key = lambda sheet: int(sheet.ParametersMap['Sheet Number'].AsString()[1:] ))

if shift >=0:
	sheetList.reverse()

for el in sheetList:	# uidoc.Selection.Elements.ReverseIterator()
	param = el.ParametersMap
	sheetNumber = param['Sheet Number'].AsString()
	sCat = sheetNumber[0:1]
	sNum = int( sheetNumber[1:] )
	newName = str( sCat + '{0:03}'.format( sNum + shift ) )
	print sheetNumber + '\t -> \t' + newName
	param['Sheet Number'].Set( newName )

t.Commit()

# __window__.Close()