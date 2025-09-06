"""Toggles visibility of section box in current 3D view"""

import pickle

from pyrevit import framework
from pyrevit import revit, DB, script
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()
active_view = revit.active_view
active_view_id_value = get_elementid_value(active_view.Id)

logger = script.get_logger()
datafile = script.get_document_data_file("SectionBox", "pym")

my_config = script.get_config()
sb_visbility = my_config.get_option("sb_visbility", True)
sb_active = my_config.get_option("sb_active", False)


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


if sb_visbility:
    with revit.Transaction("Toggle Section Box"):
        toggle_sectionbox_visibility()


# Has to be done because pickle doesn't support serializing complex .NET types
def serialize_bbox(bbox):
    return {
        "min": (bbox.Min.X, bbox.Min.Y, bbox.Min.Z),
        "max": (bbox.Max.X, bbox.Max.Y, bbox.Max.Z),
        "transform": [
            (bbox.Transform.BasisX.X, bbox.Transform.BasisX.Y, bbox.Transform.BasisX.Z),
            (bbox.Transform.BasisY.X, bbox.Transform.BasisY.Y, bbox.Transform.BasisY.Z),
            (bbox.Transform.BasisZ.X, bbox.Transform.BasisZ.Y, bbox.Transform.BasisZ.Z),
            (bbox.Transform.Origin.X, bbox.Transform.Origin.Y, bbox.Transform.Origin.Z),
        ],
    }


def deserialize_bbox(data):
    bbox = DB.BoundingBoxXYZ()

    # Min/Max
    bbox.Min = DB.XYZ(*data["min"])
    bbox.Max = DB.XYZ(*data["max"])

    # Transform
    transform = DB.Transform.Identity
    transform.BasisX = DB.XYZ(*data["transform"][0])
    transform.BasisY = DB.XYZ(*data["transform"][1])
    transform.BasisZ = DB.XYZ(*data["transform"][2])
    transform.Origin = DB.XYZ(*data["transform"][3])
    bbox.Transform = transform

    return bbox


def toggle_sectionbox_active():
    if not isinstance(active_view, DB.View3D):
        logger.error("Not a 3D view. Operation canceled.")
        return

    sectionbox_active_state = active_view.IsSectionBoxActive

    try:
        f = open(datafile, "rb")
        view_boxes = pickle.load(f)
        f.close()
    except Exception:
        view_boxes = {}

    if sectionbox_active_state:
        try:
            sectionbox = active_view.GetSectionBox()
            if sectionbox:
                view_boxes[active_view_id_value] = serialize_bbox(sectionbox)
                f = open(datafile, "wb")
                pickle.dump(view_boxes, f)
                f.close()
            active_view.IsSectionBoxActive = False
        except Exception as e:
            logger.error("Error saving section box: {}".format(e))
    else:
        try:
            if active_view_id_value in view_boxes:
                bbox_data = view_boxes[active_view_id_value]
                restored_bbox = deserialize_bbox(bbox_data)
                active_view.SetSectionBox(restored_bbox)
        except Exception as e:
            logger.error("No saved section box found or failed to load: {}".format(e))


if sb_active:
    with revit.Transaction("Toggle Section Box Active"):
        toggle_sectionbox_active()
