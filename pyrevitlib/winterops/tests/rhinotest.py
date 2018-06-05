import os.path as op

from winterops.rhino import Rhino
from winterops.tests import USER_DESKTOP


def run():
    f = Rhino.FileIO.File3dm()
    p1 = Rhino.Geometry.Point3d(0, 0, 0)
    for x in range(10):
        for y in range(10):
            for z in range(10):
                p2 = Rhino.Geometry.Point3d(x, y, z)
                line = Rhino.Geometry.Line(p1, p2)
                f.Objects.AddLine(line)

    f.Write(op.join(USER_DESKTOP, '3dmtest.3dm'), 2)
