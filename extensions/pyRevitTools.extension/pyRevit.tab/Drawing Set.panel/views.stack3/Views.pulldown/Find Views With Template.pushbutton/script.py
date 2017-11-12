"""Lists views that have a template assigned to them."""

from pyrevit import revit, DB
from pyrevit import script


output = script.get_output()


views = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Views)\
          .WhereElementIsNotElementType()\
          .ToElements()

for v in views:
    vtid = v.ViewTemplateId
    vt = revit.doc.GetElement(vtid)
    if vt:
        phasep = v.LookupParameter('Phase')
        print('TYPE: {1} ID: {2} TEMPLATE: {3} PHASE:{4} {0}'.format(
            v.ViewName,
            str(v.ViewType).ljust(20),
            output.linkify(v.Id),
            str(v.IsTemplate).ljust(10),
            phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25)))
