"""Reset all model categories and subcategories back to default."""
#pylint: disable=E0401,C0103
from pyrevit import revit
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"

logger = script.get_logger()


if forms.alert('This tool is very destructive. It resets all '
               'the element subcategories (what is shown in Object Styles '
               'panel) inside this model, effectively resetting all line '
               'styles and all other subcategory of any families imported '
               'in the model. Proceed only if you know what you are doing!\n\n'
               'Are you sure you want to proceed?', yes=True, no=True):
    if forms.alert('Are you really really sure?', yes=True, no=True):
        with revit.Transaction('Reset SubCategories'):
            revit.delete.reset_subcategories(doc=revit.doc)
