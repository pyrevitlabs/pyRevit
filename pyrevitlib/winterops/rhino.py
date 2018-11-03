import os.path as op
from winterops import clr, System, binary_path

clr.AddReference('System.Core')
clr.ImportExtensions(System.Linq)
clr.AddReferenceToFileAndPath(op.join(binary_path, 'Rhino3dmIO'))

import Rhino
