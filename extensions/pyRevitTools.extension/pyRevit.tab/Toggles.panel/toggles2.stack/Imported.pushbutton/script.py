"""Toggles visibility of imported categories on current view."""

from pyrevit import revit


@revit.carryout('Toggle Imported')
def toggle_imported():
    aview = revit.active_view
    aview.AreImportCategoriesHidden = \
        not aview.AreImportCategoriesHidden


toggle_imported()
