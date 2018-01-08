"""Changes the selected view names."""

from pyrevit import revit, DB
from pyrevit import forms


def change_case(viewlist, upper=True, verbose=False):
    with revit.Transaction('Viewnames to Upper'):
        for el in viewlist:
            if isinstance(el, DB.Viewport):
                el = revit.doc.GetElement(el.ViewId)
            orig_name = el.ViewName
            el.ViewName = orig_name.upper() if upper else orig_name.lower()
            if verbose:
                print("VIEW: {0}\n"
                      "\tRENAMED TO:\n"
                      "\t{1}\n\n".format(orig_name, el.ViewName))



selected_views = revit.get_selection()
if not selected_views:
    selected_views = [revit.activeview]


selected_option, switches = \
    forms.CommandSwitchWindow.show(
        ['to UPPERCASE',
         'to lowercase'],
        switches=['Show Report'],
        message='Select rename option:'
        )

if selected_option:
    change_case(selected_views,
                upper=True if selected_option == 'to UPPERCASE' else False,
                verbose=switches['Show Report'])
