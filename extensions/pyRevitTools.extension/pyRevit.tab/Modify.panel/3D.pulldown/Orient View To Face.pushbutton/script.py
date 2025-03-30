from pyrevit import revit, DB, UI
from pyrevit import forms

from Autodesk.Revit.UI.Selection import ObjectType

curview = revit.active_view


def reorient(view):
    try:
        # Pick face to align to using uidoc.Selection instead of revit.pick_face to get the reference instead of the face
        face_ref = revit.uidoc.Selection.PickObject(
            UI.Selection.ObjectType.Face, "Pick a face to align to:"
        )

        # Get the geometry object of the reference
        element = revit.doc.GetElement(face_ref)
        geometry_object = element.GetGeometryObjectFromReference(face_ref)

        # Check if the object might have a Transformation (by checking if it's Non-Instance)
        if isinstance(element, DB.FamilyInstance):
            # Get the transform of the family instance (converts local to world coordinates)
            transform = element.GetTransform()
            # Get the face normal in local coordinates
            local_normal = geometry_object.ComputeNormal(DB.UV(0, 0)).Normalize()
            # Apply the transform to convert normal to world coordinates
            world_normal = transform.OfVector(local_normal).Normalize()
            norm = world_normal
        else:
            norm = geometry_object.ComputeNormal(DB.UV(0, 0)).Normalize()

        # since we're working with a reference instead of the face, we can't use face.origin
        if isinstance(geometry_object, DB.Face):
            centroid = geometry_object.Evaluate(DB.UV(0.5, 0.5))
        else:
            raise Exception("The geometry object is not a face.")

        base_plane = DB.Plane.CreateByNormalAndOrigin(norm, centroid)
        # now that we have the base_plane and normal_vec
        # let's create the sketchplane
        with revit.Transaction("Orient to Selected Face"):
            sp = DB.SketchPlane.Create(revit.doc, base_plane)

            # orient the 3D view looking at the sketchplane
            view.OrientTo(norm.Negate())
            # set the sketchplane to active
            view.SketchPlane = sp

        revit.uidoc.RefreshActiveView()

    except OperationCanceledException:
        pass

    except Exception as ex:
        forms.alert("Error: {0}".format(str(ex)))


# This check could be skipped, as there is a context file in the bundle.yaml
if isinstance(curview, DB.View3D):
    reorient(curview)
else:
    forms.alert("You must be on a 3D view for this tool to work.")
