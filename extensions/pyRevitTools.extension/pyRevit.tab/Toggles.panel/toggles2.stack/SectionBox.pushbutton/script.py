"""Toggles visibility of section box in current 3D view"""

from pyrevit import framework
from pyrevit import revit,  DB


@revit.carryout('Toggle Section Box')
def toggle_sectionbox():
    # activate the show hidden so we can collect
    # all elements (visible and hidden)
    activeview = revit.active_view
    activeview.EnableRevealHiddenMode()
    view_elements = DB.FilteredElementCollector(revit.doc, activeview.Id)\
                      .OfCategory(DB.BuiltInCategory.OST_SectionBox)\
                      .ToElements()

    # find section boxes, and try toggling their visibility
    # usually more than one section box shows up on the list but not
    # all of them can be toggled. Whichever that can be toggled,
    # belongs to this view
    for sec_box in [x for x in view_elements
                    if x.CanBeHidden(activeview)]:
            if sec_box.IsHidden(activeview):
                activeview.UnhideElements(
                    framework.List[DB.ElementId]([sec_box.Id])
                    )
            else:
                activeview.HideElements(
                    framework.List[DB.ElementId]([sec_box.Id])
                    )

    activeview.DisableTemporaryViewMode(
        DB.TemporaryViewMode.RevealHiddenElements
        )


toggle_sectionbox()
