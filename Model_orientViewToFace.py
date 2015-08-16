__window__.Close()
from Autodesk.Revit.DB import Transaction, View3D, SketchPlane, Plane
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

curview = uidoc.ActiveView
ref = uidoc.Selection.PickObject( ObjectType.Face )
el = doc.GetElement( ref.ElementId )
face = el.GetGeometryObjectFromReference( ref )

if isinstance( curview, View3D):
	t = Transaction( doc, 'Orient to Selected Face')
	t.Start()
	sp = SketchPlane.Create( doc, Plane( face.Normal, face.Origin ))
	curview.OrientTo( face.Normal.Negate() )
	uidoc.ActiveView.SketchPlane = sp
	uidoc.RefreshActiveView()
	t.Commit()

# __window__.Show()
# print( ref.ElementReferenceType )
