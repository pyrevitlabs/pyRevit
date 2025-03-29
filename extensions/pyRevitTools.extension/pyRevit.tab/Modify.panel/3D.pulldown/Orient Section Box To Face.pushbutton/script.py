"""Aligns the section box of the current 3D view to selected face."""

from pyrevit.framework import Math
from pyrevit import revit, DB, UI
from pyrevit import forms


curview = revit.active_view


def orientsectionbox(view):
        try:
            # Pick face to align to
            with forms.WarningBar(title='Pick a face to align to:'):
                face = revit.pick_face()

            # Get the section box
            box = view.GetSectionBox()

            # Get the geometry object of the reference
            geometry_object = revit.doc.GetElement(face.ElementId).GetGeometryObjectFromReference(face)
            
            # Check if the object might have a Transformation (by checking if it's Non-Instance and not a System Family)
            element = revit.doc.GetElement(face.ElementId)
            if isinstance(element, DB.FamilyInstance) and element.Symbol.Family.FamilyType != DB.FamilyType.System:
                # Get the transform of the family instance (converts local to world coordinates)
                transform = element.GetTransform()
                # Get the face normal in local coordinates
                local_normal = geometry_object.ComputeNormal(DB.UV(0, 0)).Normalize()
                # Apply the transform to convert normal to world coordinates
                world_normal = transform.OfVector(local_normal).Normalize()
                norm = world_normal
            else:
                norm = face.ComputeNormal(DB.UV(0, 0)).Normalize()
            
            # Orient the box
            boxNormal = box.Transform.Basis[0].Normalize()
            angle = norm.AngleTo(boxNormal)
            axis = DB.XYZ(0, 0, 1.0)
            origin = DB.XYZ(box.Min.X + (box.Max.X - box.Min.X) / 2,
                            box.Min.Y + (box.Max.Y - box.Min.Y) / 2, 0.0)
            if norm.Y * boxNormal.X < 0:
                rotate = \
                    DB.Transform.CreateRotationAtPoint(axis, Math.PI / 2 - angle,
                                                       origin)
            else:
                rotate = DB.Transform.CreateRotationAtPoint(axis,
                                                            angle,
                                                            origin)
            box.Transform = box.Transform.Multiply(rotate)
            with revit.Transaction('Orient Section Box to Face'):
                view.SetSectionBox(box)
                revit.uidoc.RefreshActiveView()
        except Exception:
            passforms.alert('Error: {0}'.format(str(ex)))


if isinstance(curview, DB.View3D) and curview.IsSectionBoxActive:
    orientsectionbox(curview)
elif isinstance(curview, DB.View3D) and not curview.IsSectionBoxActive:
    forms.alert("The section box for View3D isn't active.")
else:
    forms.alert('You must be on a 3D view for this tool to work.')
