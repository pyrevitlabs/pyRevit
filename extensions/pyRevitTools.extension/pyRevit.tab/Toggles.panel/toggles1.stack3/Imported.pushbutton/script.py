"""Toggles visibility of imported categories on current view."""

from pyrevit import revit


@revit.carryout('Toggle Imported')
def toggle_imported():
    activeview = revit.get_activeview()
    activeview.AreImportCategoriesHidden = \
        not activeview.AreImportCategoriesHidden


toggle_imported()
