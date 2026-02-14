"""Toggles visibility, active state or a temporary section box in current 3D view"""

from pyrevit import framework
from pyrevit import revit, DB, script, forms
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()
active_view = revit.active_view
active_view_id_value = get_elementid_value(active_view.Id)

logger = script.get_logger()
DATA_SLOTNAME = "SectionBox"
TEMP_DATAFILE = script.get_instance_data_file("SectionBoxTemp")
PADDING = 1.0  # feet

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


def get_elements_bounding_box(elements):
    if not elements:
        return None

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    for elem in elements:
        try:
            bbox = elem.get_BoundingBox(None)
            if not bbox:
                continue

            min_pt = bbox.Min
            max_pt = bbox.Max

            min_x = min(min_x, min_pt.X)
            min_y = min(min_y, min_pt.Y)
            min_z = min(min_z, min_pt.Z)
            max_x = max(max_x, max_pt.X)
            max_y = max(max_y, max_pt.Y)
            max_z = max(max_z, max_pt.Z)

        except Exception:
            continue

    if min_x == float("inf"):
        return None

    new_bbox = DB.BoundingBoxXYZ()

    new_bbox.Min = DB.XYZ(min_x - PADDING, min_y - PADDING, min_z - PADDING)
    new_bbox.Max = DB.XYZ(max_x + PADDING, max_y + PADDING, max_z + PADDING)

    return new_bbox


def temp_switch_sectionbox():
    if not isinstance(active_view, DB.View3D):
        logger.error("Not a 3D view. Operation canceled.")
        return

    try:
        with open(TEMP_DATAFILE, "rb") as f:
            view_data = script.pickle.load(f)
    except Exception:
        view_data = {}

    view_key = "view_{}".format(active_view_id_value)

    if view_key in view_data:
        try:
            previous_state = view_data[view_key]

            if previous_state["was_active"]:
                restored_bbox = revit.deserialize(previous_state["bbox_data"])
                active_view.SetSectionBox(restored_bbox)
                active_view.IsSectionBoxActive = True
            else:
                active_view.IsSectionBoxActive = False

            del view_data[view_key]
            with open(TEMP_DATAFILE, "wb") as f:
                script.pickle.dump(view_data, f)

        except Exception as e:
            logger.error("Failed to restore previous state: {}".format(e))
    else:
        selection = revit.get_selection()
        if not selection:
            with forms.WarningBar(title="Pick Elements for temporary box"):
                selection = revit.pick_elements()

        try:
            current_state = {
                "was_active": active_view.IsSectionBoxActive,
                "bbox_data": None,
            }

            if active_view.IsSectionBoxActive:
                current_bbox = active_view.GetSectionBox()
                if current_bbox:
                    current_state["bbox_data"] = revit.serialize(current_bbox)

            new_bbox = get_elements_bounding_box(selection)

            if new_bbox:
                active_view.SetSectionBox(new_bbox)
                active_view.IsSectionBoxActive = True

                view_data[view_key] = current_state
                with open(TEMP_DATAFILE, "wb") as f:
                    script.pickle.dump(view_data, f)

            else:
                logger.error("Could not create bounding box from selected elements")

        except Exception as e:
            logger.error("Error creating section box: {}".format(e))


if scope == "Temporary Section Box":
    with revit.Transaction("Temporary Section Box"):
        temp_switch_sectionbox()
