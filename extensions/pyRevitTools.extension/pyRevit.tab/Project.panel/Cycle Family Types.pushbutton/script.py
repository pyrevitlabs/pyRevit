"""Cycle family types."""
#pylint: disable=E0401
from pyrevit import revit, DB
from pyrevit import forms

__title__ = "Cycle\nTypes"
__author__ = "{{author}}\nGui Talarico"


forms.check_familydoc(doc=revit.doc, exitscript=True)

family_mgr = revit.doc.FamilyManager
family_types = sorted([x.Name for x in family_mgr.Types])
if family_mgr.CurrentType:
    current_idx = family_types.index(family_mgr.CurrentType.Name)
    current_idx += 1
    if current_idx >= len(family_types):
        current_idx = 0

    with revit.Transaction('Cycle Famiy Type'):
        for ftype in family_mgr.Types:
            if ftype.Name == family_types[current_idx]:
                family_mgr.CurrentType = ftype
                revit.ui.set_statusbar_text(ftype.Name)
