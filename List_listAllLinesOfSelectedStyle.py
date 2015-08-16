from Autodesk.Revit.DB import *
import Autodesk.Revit.UI

doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

if len(selection) > 0:
	el = selection[0]
	selectedStyle = el.LineStyle

#lists all sketch based objects as:
#			ModelLine/ModelArc/ModelEllipse/...		<Sketch>
#lists all sketch based detail objects as:
#			DetailLines/DetailArc/DetailEllipse/...		whatever_style_type_it_has
cl = FilteredElementCollector(doc)
cllines = cl.OfCategory(BuiltInCategory.OST_Lines or BuiltInCategory.OST_SketchLines).WhereElementIsNotElementType()
for c in cllines:
	if c.LineStyle.Name == selectedStyle.Name:
		print( '{0:<10} {1:<25}{2:<8} {3:<15}'.format(c.Id, c.GetType().Name, c.LineStyle.Id, c.LineStyle.Name) )