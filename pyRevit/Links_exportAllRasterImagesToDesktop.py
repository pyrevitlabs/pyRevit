import os.path as op
from Autodesk.Revit.DB import FilteredElementCollector, Element, ImageType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

destDir = op.expandvars('%userprofile%\\desktop')

cl = FilteredElementCollector(doc)
list = cl.OfClass( ImageType ).ToElements()

for el in list:
	image = el.GetImage()
	imageName = op.basename( el.Path )
	# imageName = Element.Name.GetValue( el )
	print('EXPORTING: {0}'.format( imageName ))
	image.Save( op.join( destDir, imageName ))