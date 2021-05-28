"""Changes the selected view names."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import re
from pyrevit import revit, DB
from pyrevit import forms


def _lower(name):
    return name.lower()

def _upper(name):
    return name.upper()

def _camel(name):
    string = re.sub(r"(_|-)+", " ", name).title().replace(" ", "")
    return string[0].lower() + string[1:]

def _title(name):
    return name.title()

def _sentence(name):
    return name.capitalize()


CASE_FUNCTIONS = {
    'UPPER CASE': _upper,
    'lower case': _lower,
    'camel Case': _camel,
    'Title Case': _title,
    'Sentence case': _sentence,
}


def _change_case(view_list, casefunc, verbose=False):
    with revit.Transaction('Viewnames to Upper'):
        for view in view_list:
            if isinstance(view, DB.Viewport):
                view = revit.doc.GetElement(view.ViewId)
            orig_name = revit.query.get_name(view)
            revit.update.set_name(
                view,
                casefunc(orig_name)
                )
            if verbose:
                print("VIEW: {0}\n"
                      "\tRENAMED TO:\n"
                      "\t{1}\n\n".format(orig_name, revit.query.get_name(view)))


selected_views = forms.select_views(use_selection=True)

if selected_views:
    selected_option, switches = \
        forms.CommandSwitchWindow.show(
            CASE_FUNCTIONS.keys(),
            switches=['Show Report'],
            message='Select rename option:'
            )

    if selected_option:
        _change_case(selected_views,
                     casefunc=CASE_FUNCTIONS[selected_option],
                     verbose=switches['Show Report'])
