from rpw.extras.rhino import Rhino as rc


pt1 = rc.Geometry.Point3d(0, 0, 0)
pt2 = rc.Geometry.Point3d(10, 10, 0)
line1 = rc.Geometry.Line(pt1, pt2)
line1.Length
pt1 = rc.Geometry.Point3d(10, 0, 0)
pt2 = rc.Geometry.Point3d(0, 10, 0)
line2 = rc.Geometry.Line(pt1, pt2)


print(rc.Geometry.Intersect.Intersection.LineLine(line1, line2))
