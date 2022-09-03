"""Delete all instances of selected element, from model."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit.framework import List



if forms.check_selection(exitscript=True) \
        and forms.alert('This tool is very destructive. '
               'It delete family definition, and thus all the instances '
               'of selected family instances from the project. '
               'Proceed only if you know what you are doing!\n\n'
               'Are you sure you want to proceed?', yes=True, no=True):
    # get families from current selected element id's
    family_to_delete = set()
    family_names = set()
    for selected_element in revit.get_selection():
        if isinstance(selected_element, DB.FamilyInstance):
            family = selected_element.Symbol.Family
            family_to_delete.add(family.Id)
            family_names.add(family.Name)

    # delete families
    with revit.Transaction("Delete Selected Families"):
        revit.doc.Delete(List[DB.ElementId](family_to_delete))

    for fname in family_names:
        print("Deleted {}".format(fname))