from Autodesk.Revit.DB import ElementMulticategoryFilter, FilteredElementCollector, BuiltInCategory
from System.Collections.Generic import List

doc = __revit__.ActiveUIDocument.Document

#lists all sketch based objects as:
#			ModelLine/ModelArc/ModelEllipse/...		<Sketch>
#lists all sketch based detail objects as:
#			DetailLines/DetailArc/DetailEllipse/...		whatever_style_type_it_has

filter = ElementMulticategoryFilter( List[BuiltInCategory]([BuiltInCategory.OST_Lines, BuiltInCategory.OST_SketchLines]))
cl = FilteredElementCollector(doc)
cllines = cl.WherePasses( filter ).WhereElementIsNotElementType().ToElements()

for c in cllines:
	print( '{0:<10} {1:<25}{2:<8} {3:<15} {4:<20}'.format(c.Id, c.GetType().Name, c.LineStyle.Id, c.LineStyle.Name, c.Category.Name ) )