"""Changes the selected view names."""

from pyrevit import revit, DB
from pyrevit import forms


def change_case(view_list, upper=True, verbose=False):
    with revit.Transaction('Viewnames to Upper'):
        for view in view_list:
            if isinstance(view, DB.Viewport):
                view = revit.doc.GetElement(view.ViewId)
            orig_name = revit.query.get_name(view)
            revit.update.set_name(
                view,
                orig_name.upper() if upper else orig_name.lower()
                )
            if verbose:
                print("VIEW: {0}\n"
                      "\tRENAMED TO:\n"
                      "\t{1}\n\n".format(orig_name, revit.query.get_name(view)))


selected_views = forms.select_views(use_selection=True)

if selected_views:
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
