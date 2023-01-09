"""Testing Rhino.Inside modules"""
#pylint: disable=import-error,invalid-name,broad-except,wrong-import-position
#pylint: disable=global-statement,unused-import,bare-except
from pyrevit import clr, revit, DB
from pyrevit import forms
from pyrevit.framework import Enumerable
from pyrevit import script


clr.AddReference('RhinoCommon')
clr.AddReference('RhinoInside.Revit')


import Rhino
from Rhino import Geometry
from RhinoInside.Revit import Revit, Convert
from RhinoInside.Revit.Convert.Geometry import GeometryDecoder as GD

RHINO_VERSION = -1

logger = script.get_logger()
output = script.get_output()


def ensure_rir():
    """Ensure Rhino.Inside.Revit is loaded"""
    global RHINO_VERSION
    try:
        RHINO_VERSION = Rhino.RhinoApp.ExeVersion
    except:
        forms.alert("Rhino.Inside.Revit is not available", exitscript=True)


# make sure Rhino.Inside.Revit is loaded
ensure_rir()

with revit.Transaction("Rhino.Inside Sample7"):
    sphere = Geometry.Sphere(Geometry.Point3d.Origin, GD.ToModelLength(12))
    brep = sphere.ToBrep()
    meshes = \
        Geometry.Mesh.CreateFromBrep(brep, Geometry.MeshingParameters.Default)

    category = DB.ElementId(DB.BuiltInCategory.OST_GenericModel)
    ds = DB.DirectShape.CreateElement(revit.doc, category)

    solids = []
    for mesh in meshes:
        solid = Convert.Geometry.GeometryEncoder.ToSolid(mesh)
        solids.append(solid)

    for geometry in solids:
        ds.AppendShape([geometry])
