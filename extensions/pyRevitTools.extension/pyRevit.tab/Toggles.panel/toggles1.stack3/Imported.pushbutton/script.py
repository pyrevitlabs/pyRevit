"""Toggles visibility of imported categories on current view"""

# from rpw import activeview, Action
from revitutils import curview, Action
activeview = curview


with Action('Toggle Imported'):
    activeview.AreImportCategoriesHidden = \
        not activeview.AreImportCategoriesHidden
