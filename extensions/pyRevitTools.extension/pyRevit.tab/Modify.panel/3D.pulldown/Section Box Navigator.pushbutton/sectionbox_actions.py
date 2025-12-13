from pyrevit import revit, script, forms
from pyrevit.framework import List, Math
from pyrevit.compat import get_elementid_value_func
from pyrevit import DB, UI

get_elementid_value = get_elementid_value_func()

logger = script.get_logger()


def toggle(doc, datafilename):
    """Toggle section box."""
    current_view = doc.ActiveView
    if not isinstance(current_view, DB.View3D):
        return
    current_view_id_value = get_elementid_value(current_view.Id)
    sectionbox_active_state = current_view.IsSectionBoxActive

    try:
        view_boxes = script.load_data(datafilename)
    except Exception:
        view_boxes = {}

    with revit.Transaction("Toggle SectionBox"):
        if sectionbox_active_state:
            try:
                sectionbox = current_view.GetSectionBox()
                if sectionbox:
                    view_boxes[current_view_id_value] = revit.serialize(sectionbox)
                    script.store_data(datafilename, view_boxes)
                current_view.IsSectionBoxActive = False
            except Exception as ex:
                logger.error("Error saving section box: {}".format(ex))
        else:
            try:
                if current_view_id_value in view_boxes:
                    bbox_data = view_boxes[current_view_id_value]
                    restored_bbox = revit.deserialize(bbox_data)
                    current_view.SetSectionBox(restored_bbox)
            except Exception as ex:
                logger.error(
                    "No saved section box found or failed to load: {}".format(ex)
                )


def hide(doc):
    """Hide or Unhide section box."""
    current_view = doc.ActiveView
    if not isinstance(current_view, DB.View3D):
        return
    with revit.Transaction("Toggle SB visbility"):
        current_view.EnableRevealHiddenMode()
        view_elements = (
            DB.FilteredElementCollector(doc, current_view.Id)
            .OfCategory(DB.BuiltInCategory.OST_SectionBox)
            .ToElements()
        )
        was_hidden = None  # store previous state

        for sec_box in [x for x in view_elements if x.CanBeHidden(current_view)]:
            was_hidden = sec_box.IsHidden(current_view)

            if was_hidden:
                current_view.UnhideElements(List[DB.ElementId]([sec_box.Id]))
            else:
                current_view.HideElements(List[DB.ElementId]([sec_box.Id]))

        current_view.DisableTemporaryViewMode(DB.TemporaryViewMode.RevealHiddenElements)

    return was_hidden


def align_to_face(doc, uidoc):
    """Align to face"""
    current_view = doc.ActiveView
    if not isinstance(current_view, DB.View3D):
        return
    try:
        with forms.WarningBar(title="Pick a face on a solid object"):
            reference = uidoc.Selection.PickObject(
                UI.Selection.ObjectType.PointOnElement,
                "Pick a face on a solid object",
            )

        instance = doc.GetElement(reference.ElementId)
        picked_point = reference.GlobalPoint

        if isinstance(instance, DB.RevitLinkInstance):
            linked_doc = instance.GetLinkDocument()
            linked_element_id = reference.LinkedElementId
            element = linked_doc.GetElement(linked_element_id)
            transform = instance.GetTransform()
        else:
            element = instance
            transform = DB.Transform.Identity

        # Get geometry
        geom_objs = revit.query.get_geometry(
            element,
            include_invisible=True,
            compute_references=True,
            detail_level=current_view.DetailLevel,
        )

        solids = [
            g for g in geom_objs if isinstance(g, DB.Solid) and g.Faces.Size > 0
        ]

        # Find face that contains the picked point
        target_face = None
        for solid in solids:
            for face in solid.Faces:
                try:
                    result = face.Project(picked_point)
                    if result and result.XYZPoint.DistanceTo(picked_point) < 1e-6:
                        target_face = face
                        break
                except Exception:
                    continue
            if target_face:
                break

        if not target_face:
            forms.alert(
                "Couldn't find a face at the picked point.", exitscript=True
            )

        local_normal = target_face.ComputeNormal(DB.UV(0.5, 0.5)).Normalize()
        world_normal = transform.OfVector(local_normal).Normalize()

        # --- Orient section box ---
        box = current_view.GetSectionBox()
        box_normal = box.Transform.BasisX.Normalize()
        angle = world_normal.AngleTo(box_normal)

        # Choose rotation axis - Z axis in world coordinates
        axis = DB.XYZ(0, 0, 1.0)
        origin = DB.XYZ(
            box.Min.X + (box.Max.X - box.Min.X) / 2,
            box.Min.Y + (box.Max.Y - box.Min.Y) / 2,
            box.Min.Z,
        )

        if world_normal.Y * box_normal.X < 0:
            rotate = DB.Transform.CreateRotationAtPoint(
                axis, Math.PI / 2 - angle, origin
            )
        else:
            rotate = DB.Transform.CreateRotationAtPoint(axis, angle, origin)

        box.Transform = box.Transform.Multiply(rotate)

        with revit.Transaction("Orient Section Box to Face"):
            current_view.SetSectionBox(box)
            uidoc.RefreshActiveView()

    except Exception as ex:
        logger.error("Error: {}".format(str(ex)))
