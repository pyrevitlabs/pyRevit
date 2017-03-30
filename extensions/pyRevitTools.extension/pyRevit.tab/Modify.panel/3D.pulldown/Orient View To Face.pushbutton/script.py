from pyrevit import HOST_APP
from revitutils import doc, uidoc, selection, curview
from revitutils import Action

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import View3D, SketchPlane, Plane, UV


__doc__ = 'Reorients the current 3D view camera, perpendicular to the selected face. ' \
          'This tool will set a sketch plane over the selected face for 3d drawing.'


face = selection.utils.pick_face()


if face and isinstance(curview, View3D):
    with Action('Orient to Selected Face'):
        if HOST_APP.is_newer_than(2015):
            normal_vec = face.ComputeNormal(UV(0,0))
            sp = SketchPlane.Create(doc, Plane(normal_vec, face.Origin))
            curview.OrientTo(normal_vec.Negate())
        else:
            sp = SketchPlane.Create(doc, Plane(face.Normal, face.Origin))
            curview.OrientTo(face.Normal.Negate())
        uidoc.ActiveView.SketchPlane = sp
        uidoc.RefreshActiveView()
