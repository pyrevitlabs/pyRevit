from pyrevit.interop.rhino import Rhino


pt1 = Rhino.Geometry.Point3d(0, 0, 0)
pt2 = Rhino.Geometry.Point3d(10, 10, 0)
line1 = Rhino.Geometry.Line(pt1, pt2)
line1.Length
pt1 = Rhino.Geometry.Point3d(10, 0, 0)
pt2 = Rhino.Geometry.Point3d(0, 10, 0)
line2 = Rhino.Geometry.Line(pt1, pt2)


print(Rhino.Geometry.Intersect.Intersection.LineLine(line1, line2))
