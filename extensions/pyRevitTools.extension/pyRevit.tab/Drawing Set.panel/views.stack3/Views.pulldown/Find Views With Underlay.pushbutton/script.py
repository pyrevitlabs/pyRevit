"""Lists views that have an active underlay."""

from pyrevit import HOST_APP

from scriptutils import this_script
from revitutils import doc, uidoc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

for v in views:
    phasep = v.LookupParameter('Phase')
    try:
        if HOST_APP.version == '2017':
            base_underlay_param = v.LookupParameter('Range: Base Level')
            top_underlay_param = v.LookupParameter('Range: Top Level')
            if base_underlay_param \
            and top_underlay_param \
            and base_underlay_param.AsValueString() != 'None' \
            and top_underlay_param.AsValueString() != 'None':
                print('TYPE: {1}\n' \
                      'ID: {2}\n' \
                      'TEMPLATE: {3}\n' \
                      'UNDERLAY (BASE):{4}\n' \
                      'UNDERLAY (TOP):{5}\n' \
                      '{0}\n\n'.format(v.ViewName,
                                       str(v.ViewType).ljust(20),
                                       this_script.output.linkify(v.Id),
                                       str(v.IsTemplate).ljust(10),
                                       base_underlay_param.AsValueString().ljust(25),
                                       top_underlay_param.AsValueString().ljust(25)))
        else:
            underlayp = v.LookupParameter('Underlay')
            if underlayp and underlayp.AsValueString() != 'None':
                print('TYPE: {1}\n' \
                      'ID: {2}\n' \
                      'TEMPLATE: {3}\n' \
                      'UNDERLAY:{4}\n' \
                      '{0}\n\n'.format(v.ViewName,
                                       str(v.ViewType).ljust(20),
                                       this_script.output.linkify(v.Id),
                                       str(v.IsTemplate).ljust(10),
                                       underlayp.AsValueString().ljust(25)))
    except:
        continue
