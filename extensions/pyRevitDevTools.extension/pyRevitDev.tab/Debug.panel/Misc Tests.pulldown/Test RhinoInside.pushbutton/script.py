"""Testing Rhino.Inside modules"""
#pylint: disable=import-error,invalid-name,broad-except,wrong-import-position
from pyrevit import clr, revit, DB
from pyrevit.framework import Enumerable
from pyrevit import script


clr.AddReference('RhinoCommon')
clr.AddReference('RhinoInside.Revit')


from Rhino import Geometry
from RhinoInside.Revit import Revit, Convert


logger = script.get_logger()
output = script.get_output()


with revit.Transaction("Rhino.Inside Sample7"):
    sphere = Geometry.Sphere(Geometry.Point3d.Origin, 12 * Revit.ModelUnits)
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
