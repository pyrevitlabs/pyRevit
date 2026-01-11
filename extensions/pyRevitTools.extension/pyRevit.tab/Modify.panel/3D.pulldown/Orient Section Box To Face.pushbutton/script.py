"""Aligns the section box of the current 3D view to selected face."""

from pyrevit.framework import Math
from pyrevit import revit, DB, UI, forms


curview = revit.active_view
uidoc = revit.uidoc
doc = revit.doc


def orientsectionbox(view):
    try:
        world_normal = None

        reference = uidoc.Selection.PickObject(
            UI.Selection.ObjectType.PointOnElement, "Pick a face on a solid object"
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

        geom_objs = revit.query.get_geometry(
            element,
            include_invisible=True,
            compute_references=True,
            detail_level=view.DetailLevel
        )

        solids = [g for g in geom_objs if isinstance(g, DB.Solid) and g.Faces.Size > 0]

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
            forms.alert("Couldn't find a face at the picked point.", exitscript=True)

        local_normal = target_face.ComputeNormal(DB.UV(0.5, 0.5)).Normalize()
        world_normal = transform.OfVector(local_normal).Normalize()

        # --- Orient section box ---
        box = view.GetSectionBox()
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
            view.SetSectionBox(box)
            revit.uidoc.RefreshActiveView()

    except Exception as ex:
        forms.alert("Error: {}".format(str(ex)))


if isinstance(curview, DB.View3D) and curview.IsSectionBoxActive:
    orientsectionbox(curview)
elif isinstance(curview, DB.View3D) and not curview.IsSectionBoxActive:
    forms.alert("The section box for View3D isn't active.")
else:
    forms.alert("You must be on a 3D view for this tool to work.")
