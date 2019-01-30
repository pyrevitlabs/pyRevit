"""Test pythonnet integration"""
# pylint: skip-file
import os
import sys
import os.path as op

import clr
clr.AddReference('Python.Runtime')
import Python as py

TEST_CODE = """import sys
print('\\n'.join(sys.path))

import System
print(System)
"""

pe = py.Runtime.PythonEngine

if not pe.IsInitialized:
    pe.Initialize()

try:
    # with py.Runtime.Py.GIL():
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
    # pe.Shutdown()
    pass