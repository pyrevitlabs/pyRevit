# pylama:ignore=E402,W0611
import os.path as op
from winterops import clr, System, binary_path

clr.AddReferenceToFileAndPath(op.join(binary_path, 'Ifc.Net'))

import Ifc4
