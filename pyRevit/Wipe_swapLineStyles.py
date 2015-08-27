from Autodesk.Revit.DB import Transaction, FilteredElementCollector, BuiltInCategory, ElementId
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
curview = doc.ActiveView

verbose = True

with Transaction(doc, 'Swap Line Styles') as t:
	t.Start()

	sel = []
	fromStyleLine = doc.GetElement( uidoc.Selection.PickObject(ObjectType.Element, 'Pick a line with the style to be replaced.') )
	fromStyle = fromStyleLine.LineStyle
	toStyleLine = doc.GetElement( uidoc.Selection.PickObject(ObjectType.Element, 'Pick a line with the source style.') )
	toStyle = toStyleLine.LineStyle

	linelist = []

	cl = FilteredElementCollector(doc)
	cllines = cl.OfCategory( BuiltInCategory.OST_Lines or BuiltInCategory.OST_SketchLines ).WhereElementIsNotElementType()
	for c in cllines:
		if c.LineStyle.Name == fromStyle.Name:
			linelist.append(c)
			# print( '{0:<10} {1:<25}{2:<8} {3:<15}'.format(c.Id, c.GetType().Name, c.LineStyle.Id, c.LineStyle.Name) )

	if len(linelist) > 100:
		verbose = False
	for line in linelist:
		if line.Category.Name != '<Sketch>' and line.GroupId < ElementId(0):
			if verbose:
				print( 'LINE FOUND:\t{0:<10} {1:<25}{2:<8} {3:<15}'.format(line.Id, line.GetType().Name, line.LineStyle.Id, line.LineStyle.Name) )
			line.LineStyle = toStyle
		elif line.Category.Name == '<Sketch>':
			print( 'SKIPPED <Sketch> Line ----:\n           \t{0:<10} {1:<25}{2:<8} {3:<15}\n'.format(line.Id, line.GetType().Name, line.LineStyle.Id, line.LineStyle.Name) )
		elif line.GroupId > ElementId(0):
			print( 'SKIPPED Grouped Line ----:\n           \t{0:<10} {1:<25}{2:<8} {3:<15} {4:<10}\n'.format(line.Id, line.GetType().Name, line.LineStyle.Id, line.LineStyle.Name, doc.GetElement(line.GroupId).Name ))

	t.Commit()
