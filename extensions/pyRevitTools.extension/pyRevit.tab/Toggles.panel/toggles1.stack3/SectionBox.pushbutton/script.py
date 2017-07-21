"""Toggles visibility of section box in current 3D view"""

from revitutils import doc, uidoc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, \
                              ElementId, Transaction, TemporaryViewMode
from System.Collections.Generic import List


t = Transaction(doc, 'Toggle Section Box')
t.Start()

# activate the show hidden so we can collect all elements (visible and hidden)
activeview = uidoc.ActiveView
activeview.EnableRevealHiddenMode()
view_elements = FilteredElementCollector(doc, uidoc.ActiveView.Id) \
                .OfCategory(BuiltInCategory.OST_SectionBox).ToElements()

# find section boxes, and try toggling their visibility
# usually more than one section box shows up on the list but not
# all of them can be toggled. Whichever that can be toggled,
# belongs to this view
for sec_box in [x for x in view_elements
                  if x.CanBeHidden(uidoc.ActiveView)]:
        if sec_box.IsHidden(activeview):
            activeview.UnhideElements(List[ElementId]([sec_box.Id]))
        else:
            activeview.HideElements(List[ElementId]([sec_box.Id]))

activeview.DisableTemporaryViewMode(TemporaryViewMode.RevealHiddenElements)
t.Commit()
