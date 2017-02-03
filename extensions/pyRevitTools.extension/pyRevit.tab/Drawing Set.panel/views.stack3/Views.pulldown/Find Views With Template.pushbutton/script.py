"""Lists views that have a template assigned to them."""

from scriptutils import this_script
from revitutils import doc, uidoc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

for v in views:
    vtid = v.ViewTemplateId
    vt = doc.GetElement(vtid)
    if vt:
        phasep = v.LookupParameter('Phase')
        print('TYPE: {1} ID: {2} TEMPLATE: {3} PHASE:{4} {0}'.format(
            v.ViewName,
            str(v.ViewType).ljust(20),
            this_script.output.linkify(v.Id),
            str(v.IsTemplate).ljust(10),
            phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25)))
