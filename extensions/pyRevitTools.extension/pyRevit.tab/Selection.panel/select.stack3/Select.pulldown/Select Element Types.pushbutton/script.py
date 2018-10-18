"""Select all element types of chosen category."""
#pylint: disable=E0401,W0703,C0103
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


# collect all element types
element_types = \
    {x.FamilyName
     for x in revit.query.get_types_by_class(DB.ElementType, doc=revit.doc)
     if x.FamilyName}

selected_option = \
    forms.CommandSwitchWindow.show(list(element_types),
                                   message='Pick type category:')

if selected_option:
    all_types = \
        revit.query.get_types_by_class(DB.ElementType, doc=revit.doc)
    selection = revit.get_selection()
    selection.set_to([x for x in all_types
                      if x.FamilyName == selected_option
                      and revit.ElementWrapper(x).name != x.FamilyName])
