"""Test pythonnet integration"""
# pylint: skip-file
import os
import sys
import os.path as op

__context__ = 'zero-doc'

import clr
# add path of active pyRevitLabs.PythonNet.dll to the sys.path
from pyrevit.userconfig import user_config
sys.path.append(op.dirname(user_config.get_active_cpython_engine().AssemblyPath))
print('\n'.join(sys.path))
# now load the cpython assembly
# clr.AddReference('pyRevitLabs.PythonNet')
clr.AddReferenceToFile('pyRevitLabs.PythonNet.dll')
import pyRevitLabs.PythonNet as py

TEST_CODE = """import sys
print('\\n'.join(sys.path))

import System
print(System)
"""

pe = py.PythonEngine

if not pe.IsInitialized:
    pe.Initialize()

try:
    # with py.Py.GIL():
    # print version
    print(pe.Version)

    # import
    print(pe.ImportModule("os"))
    csys = pe.ImportModule("sys")

    # set stdout to output stream for this command
    csys.stdout = sys.stdout

    # code exec test
    pe.Exec(TEST_CODE)

    # test adsk modules
    print(pe.ImportModule("Autodesk.Revit.DB"))
    print(pe.ImportModule("Autodesk.Revit.UI"))

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