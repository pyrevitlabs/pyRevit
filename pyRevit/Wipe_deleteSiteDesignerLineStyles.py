from __future__ import print_function
from Autodesk.Revit.DB import Transaction
import StringIO

doc = __revit__.ActiveUIDocument.Document
outputs = StringIO.StringIO()
catsToDelete = []

def report(message):
	#print(message)
	outputs.write(message)
	outputs.write('\n')


#COLLECT CATS - METHOD 1
report('Finding Line Styles using Method 1...')
linesCat = doc.Settings.Categories.get_Item("Lines")
for cat in linesCat.SubCategories:
	if 'SW' == cat.Name[:2]:
		catsToDelete.append( cat )

#COLLECT CATS - METHOD 2
report('Finding Line Styles using Method 2...')
from Autodesk.Revit.DB import ElementMulticategoryFilter, FilteredElementCollector, BuiltInCategory
from System.Collections.Generic import List
filter = ElementMulticategoryFilter( List[BuiltInCategory]([BuiltInCategory.OST_Lines]))
cl = FilteredElementCollector(doc)
cllines = list( cl.WherePasses( filter ).WhereElementIsNotElementType().ToElements() )
styleIds = cllines[0].GetLineStyleIds()

for styleId in styleIds:
	style = doc.GetElement( styleId )
	cat = style.GraphicsStyleCategory
	if 'SW' == cat.Name[:2]:
		catsToDelete.append( cat )

#DELETE CATS
total = len( catsToDelete )
report('Deleting {0} Line Styles...'.format( total))
report('Deleted Line Styles:')
step = 1/ 50.0
threshold = step
t = Transaction(doc, 'Delete all SW Lines') 
t.Start()
for i, cat in enumerate(catsToDelete):
	try:
		report('ID: {0}\tNAME: {1}'.format(cat.Id, cat.Name) )
		doc.Delete( cat.Id )
		if i / float(total) >= threshold:
			report('|', end='')
			threshold += step
	except:
		continue
t.Commit()

report( '\n\n' )
print( outputs.getvalue() )