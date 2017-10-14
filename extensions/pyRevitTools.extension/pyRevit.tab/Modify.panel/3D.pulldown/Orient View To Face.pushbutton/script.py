from pyrevit import HOST_APP
from revitutils import doc, uidoc, selection, curview

# noinspection PyUnresolvedReferences
import Autodesk.Revit.DB as DB


__doc__ = 'Reorients the current 3D view camera, perpendicular to the' \
          'selected face. This tool will set a sketch plane over the ' \
          'selected face for 3d drawing.'


face = selection.utils.pick_face()


if face and isinstance(curview, DB.View3D):
    t = DB.Transaction(doc, 'Orient to Selected Face')
    t.Start()

    # calculate normal
    if HOST_APP.is_newer_than(2015):
        normal_vec = face.ComputeNormal(DB.UV(0, 0))
    else:
        normal_vec = face.Normal

    # create base plane for sketchplane
    if HOST_APP.is_newer_than(2016):
        base_plane = DB.Plane.CreateByNormalAndOrigin(normal_vec, face.Origin)
    else:
        base_plane = DB.Plane(normal_vec, face.Origin)

    # now that we have the base_plane and normal_vec
    # let's create the sketchplane
    sp = DB.SketchPlane.Create(doc, base_plane)

    # orient the 3D view looking at the sketchplane
    curview.OrientTo(normal_vec.Negate())
    # set the sketchplane to active
    uidoc.ActiveView.SketchPlane = sp

    t.Commit()

    uidoc.RefreshActiveView()
