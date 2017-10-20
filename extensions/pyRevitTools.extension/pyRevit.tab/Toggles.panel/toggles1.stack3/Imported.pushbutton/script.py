"""Toggles visibility of imported categories on current view."""

from pyrevit.revit import doc


@doc.carryout('Toggle Imported')
def toggle_imported():
    activeview = doc.get_activeview()
    activeview.AreImportCategoriesHidden = \
        not activeview.AreImportCategoriesHidden


toggle_imported()
