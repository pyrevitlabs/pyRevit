import sys
import os.path as op

sys.path.append(op.dirname(__file__))

from pyrevit.framework import clr, System   # noqa

clr.AddReference("System.Core")
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName('Rhino3dmIO')

from Rhino import *     # noqa
