"""Test pythonnet integration"""
# pylint: skip-file
import os
import sys
import os.path as op

__context__ = 'zero-doc'

import clr
# add path of pyRevitLabs.PythonNet.dll to the sys.path
from pyrevit import BIN_DIR
sys.path.append(BIN_DIR)
print('\n'.join(sys.path))
# now load the cpython assembly
clr.AddReferenceToFile('pyRevitLabs.PythonNet.dll')
from Python.Runtime import PythonEngine, PyModule

TEST_CODE = """import sys
print('\\n'.join(sys.path))

import System
print(System)
"""

pe = PythonEngine

if not pe.IsInitialized:
    pe.Initialize()

try:
    # print version
    print(pe.Version)

    # import
    print(PyModule.Import("os"))
    csys = PyModule.Import("sys")

    # set stdout to output stream for this command
    csys.stdout = sys.stdout

    # code exec test
    pe.Exec(TEST_CODE)

    # test adsk modules
    print(PyModule.Import("Autodesk.Revit.DB"))
    print(PyModule.Import("Autodesk.Revit.UI"))

    # eval
    print(pe.Eval("{1:2, 3:4}").GetPythonType())
    print(pe.Eval("[1, 2, 3]").GetPythonType())
except Exception as e:
    print(e)
finally:
    # somehow shutting down thru ironpython doesn't crash revit
    # button shutting it down mid session with break the next runs
    # pe.Shutdown()
    pass
