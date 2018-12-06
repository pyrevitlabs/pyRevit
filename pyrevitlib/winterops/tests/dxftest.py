import os.path as op

from winterops import System
from winterops.dxf import Dxf
from winterops.tests import USER_DESKTOP


def run():
    dxf_file = Dxf.DxfFile()
    for x in range(10):
        for y in range(10):
            for z in range(10):
                line = Dxf.Entities.DxfLine(Dxf.DxfPoint(0, 0, 0),
                                            Dxf.DxfPoint(x, y, z))
                dxf_file.Entities.Add(line)

    fs = System.IO.FileStream(op.join(USER_DESKTOP, 'dxftest.dxf'),
                              System.IO.FileMode.Create)
    dxf_file.Save(fs)
    fs.Close()
