"""Lists views based on a search option."""

from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


output = script.get_output()


views = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Views)\
          .WhereElementIsNotElementType()\
          .ToElements()


def find_views_with_underlay():
    for v in views:
        try:
            if HOST_APP.version == '2017':
                base_underlay_param = v.LookupParameter('Range: Base Level')
                top_underlay_param = v.LookupParameter('Range: Top Level')
                if base_underlay_param \
                        and top_underlay_param \
                        and base_underlay_param.AsValueString() != 'None' \
                        and top_underlay_param.AsValueString() != 'None':
                    print('TYPE: {1}\n'
                          'ID: {2}\n'
                          'TEMPLATE: {3}\n'
                          'UNDERLAY (BASE):{4}\n'
                          'UNDERLAY (TOP):{5}\n'
                          '{0}\n\n'
                          .format(v.ViewName,
                                  str(v.ViewType).ljust(20),
                                  output.linkify(v.Id),
                                  str(v.IsTemplate).ljust(10),
                                  base_underlay_param.AsValueString().ljust(25),
                                  top_underlay_param.AsValueString().ljust(25)))
            else:
                underlayp = v.LookupParameter('Underlay')
                if underlayp and underlayp.AsValueString() != 'None':
                    print('TYPE: {1}\n'
                          'ID: {2}\n'
                          'TEMPLATE: {3}\n'
                          'UNDERLAY:{4}\n'
                          '{0}\n\n'.format(v.ViewName,
                                           str(v.ViewType).ljust(20),
                                           output.linkify(v.Id),
                                           str(v.IsTemplate).ljust(10),
                                           underlayp.AsValueString().ljust(25)))
        except Exception:
            continue


def find_view_with_template():
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
                phasep.AsValueString().ljust(25)
                if phasep else '---'.ljust(25)
                )
            )


selected_option = \
    forms.CommandSwitchWindow.show(
        ['with underlay',
         'with template'],
        message='Select search option:'
        )

if selected_option == 'with underlay':
    find_views_with_underlay()
elif selected_option == 'with template':
    find_view_with_template()
