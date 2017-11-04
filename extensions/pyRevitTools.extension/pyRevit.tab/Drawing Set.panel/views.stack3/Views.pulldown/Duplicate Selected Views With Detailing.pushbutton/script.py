"""Batch duplicates the selected views WITH detailing."""

from pyrevit import revit, DB


with revit.Transaction('Duplicate selected views'):
    for el_id in revit.get_selection().element_ids:
        el = revit.doc.GetElement(el_id)
        el.Duplicate(DB.ViewDuplicateOption.WithDetailing)
