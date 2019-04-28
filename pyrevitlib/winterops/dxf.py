import os.path as op
from winterops import clr, System, binary_path

clr.AddReferenceToFileAndPath(op.join(binary_path, 'IxMilia.Dxf'))

from IxMilia import Dxf
