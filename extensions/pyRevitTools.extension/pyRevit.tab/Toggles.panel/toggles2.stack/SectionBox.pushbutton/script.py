"""Toggles visibility of section box in current 3D view"""

from pyrevit import framework
from pyrevit import revit, DB, script
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()
active_view = revit.active_view
active_view_id_value = get_elementid_value(active_view.Id)

logger = script.get_logger()
DATA_SLOTNAME = "SectionBox"

my_config = script.get_config()
scope = my_config.get_option("scope", "Visibility")


def toggle_sectionbox_visibility():
    # activate the show hidden so we can collect
    # all elements (visible and hidden)
    active_view.EnableRevealHiddenMode()
    view_elements = (
        DB.FilteredElementCollector(revit.doc, active_view.Id)
        .OfCategory(DB.BuiltInCategory.OST_SectionBox)
        .ToElements()
    )

    # find section boxes, and try toggling their visibility
    # usually more than one section box shows up on the list but not
    # all of them can be toggled. Whichever that can be toggled,
    # belongs to this view
    for sec_box in [x for x in view_elements if x.CanBeHidden(active_view)]:
        if sec_box.IsHidden(active_view):
            active_view.UnhideElements(framework.List[DB.ElementId]([sec_box.Id]))
        else:
            active_view.HideElements(framework.List[DB.ElementId]([sec_box.Id]))

    active_view.DisableTemporaryViewMode(DB.TemporaryViewMode.RevealHiddenElements)


if scope == "Visibility":
    with revit.Transaction("Toggle Section Box Visible"):
        toggle_sectionbox_visibility()


def toggle_sectionbox_active():
    if not isinstance(active_view, DB.View3D):
        logger.error("Not a 3D view. Operation canceled.")
        return

    try:
        view_boxes = script.load_data(DATA_SLOTNAME)
    except Exception:
        view_boxes = {}

    if active_view.IsSectionBoxActive:
        try:
            sectionbox = active_view.GetSectionBox()
            if sectionbox:
                view_boxes[active_view_id_value] = revit.serialize(sectionbox)
                script.store_data(DATA_SLOTNAME, view_boxes)
            active_view.IsSectionBoxActive = False
        except Exception as e:
            logger.error("Error saving section box: {}".format(e))
    else:
        try:
            if active_view_id_value in view_boxes:
                bbox_data = view_boxes[active_view_id_value]
                restored_bbox = revit.deserialize(bbox_data)
                active_view.SetSectionBox(restored_bbox)
        except Exception as e:
            logger.error("No saved section box found or failed to load: {}".format(e))


if scope == "Active State":
    with revit.Transaction("Toggle Section Box Active"):
        toggle_sectionbox_active()
