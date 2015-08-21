from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(views, key=lambda x: x.SheetNumber)

sheetCategories = {
'A0':'A0XX - SITE',
'AD0':'A0XX - SITE',
'A1':'A1XX - CODE',
'A2':'A2XX - PLANS',
'AD2':'A2XX - PLANS',
'A3':'A3XX - ROOF',
'A4':'A4XX - RCP',
'A5':'A5XX - EXTERIOR',
'A6':'A6XX - SECTIONS',
'A7':'A7XX - DOOR & WINDOW',
'A8':'A8XX - INTERIOR',
'A90':'A90XX - DET SITE',
'A91':'A91XX - DET CODE',
'A92':'A92XX - DET PLANS',
'A93':'A93XX - DET ROOF',
'A94':'A94XX - DET RCP',
'A95':'A95XX - DET EXTERIOR',
'A96':'A96XX - DET SECTIONS',
'A97':'A97XX - DET DOOR & WINDOW',
'A98':'A98XX - DET INTERIOR',
}

possibleParameters = ['Sheet Description', 'Sheet Location']

t = Transaction(doc, 'Batch Organize Sheets') 
t.Start()

for el in sheets:
	for param in possibleParameters:
		pdesc = el.GetParameters( param )
		if len( pdesc ) == 0:
			continue
		else:
			pdesc = pdesc[0]
			break
	snum = el.SheetNumber[:2]
	if snum == 'A9':
		snum = el.SheetNumber[:3]
	elif snum == 'AD':
		snum = el.SheetNumber[:3]
	try:
		cat = sheetCategories[snum]
		print('Organizing:\t{0}\n        as:\t{1}\n'.format(el.SheetNumber, cat))
		pdesc.Set( sheetCategories[snum] )
	except KeyError:
		continue

t.Commit()