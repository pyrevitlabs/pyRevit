from Autodesk.Revit.DB import FilteredElementCollector, Transaction, LinePatternElement
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc).OfClass(LinePatternElement).ToElements()

t = Transaction(doc, 'Remove IMPORT Patterns')
t.Start()

for lp in cl:
	if lp.Name.lower().startswith( 'import' ):
		print('\nIMPORTED LINETYPE FOUND:\n{0}'.format( lp.Name ))
		doc.Delete( lp.Id )
		print('--- DELETED ---')

t.Commit()