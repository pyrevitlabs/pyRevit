"""Lists all lines in the model with matching style to the selected line.
lists all sketch based objects as:
        ModelLine/ModelArc/ModelEllipse/...         <Sketch>
lists all sketch based detail objects as:
        DetailLines/DetailArc/DetailEllipse/...     whatever_style_type_it_has
"""

from scriptutils import doc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

if selection.first:
    selectedStyle = selection.first.LineStyle

    cl = FilteredElementCollector(doc)
    cllines = cl.OfCategory(BuiltInCategory.OST_Lines or BuiltInCategory.OST_SketchLines).WhereElementIsNotElementType()

    for c in cllines:
        if c.LineStyle.Name == selectedStyle.Name:
            print('{0:<10} {1:<25}{2:<8} {3:<15}'.format(c.Id, c.GetType().Name, c.LineStyle.Id, c.LineStyle.Name))
