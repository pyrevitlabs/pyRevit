#! python3
"""Test CPython engine: .NET interop, Revit API access, pyrevit imports,
eval/exec, stdlib modules, and unicode support."""
# pylint: skip-file
import sys
import os

__context__ = 'zero-doc'

print('Python version: {}'.format(sys.version))
print('\n## sys.path:')
print('\n'.join(sys.path))

# Test .NET interop via pythonnet
print('\n## pythonnet interop:')
import clr
import System
print('System: {}'.format(System))
print('CLR: {}'.format(clr))

# Test Revit API access
print('\n## Revit API:')
import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI as UI
print('Autodesk.Revit.DB: {}'.format(DB))
print('Autodesk.Revit.UI: {}'.format(UI))

# Test eval and exec
print('\n## eval/exec:')
result = eval("{1:2, 3:4}")
print('eval dict: {} (type: {})'.format(result, type(result)))
result = eval("[1, 2, 3]")
print('eval list: {} (type: {})'.format(result, type(result)))

exec("print('exec test: hello from exec')")

# Test pyrevit import
print('\n## pyrevit:')
import pyrevit
from pyrevit import revit
print('pyrevit: {}'.format(pyrevit))
print('revit module: {}'.format(revit))

# Test Revit document access
print('\n## Revit document:')
try:
    doc = __revit__.ActiveUIDocument.Document
    print('Active document: {}'.format(doc.Title))

    from pyrevit.compat import get_elementid_value_func
    get_eid = get_elementid_value_func()

    walls = DB.FilteredElementCollector(doc)\
              .OfClass(DB.Wall)\
              .WhereElementIsNotElementType()\
              .ToElements()
    print('Walls found: {}'.format(len(walls)))
    for i in range(min(5, len(walls))):
        print('  {} id:{}'.format(walls[i], get_eid(walls[i].Id)))
    if len(walls) > 5:
        print('  ... and {} more'.format(len(walls) - 5))
except Exception as ex:
    print('Document test skipped: {}'.format(ex))

# Test standard library modules
print('\n## stdlib:')
import json
print('json: {}'.format(json.dumps({"test": True})))
import pathlib
print('pathlib: {}'.format(pathlib.Path(os.getcwd())))

# Test unicode
print('\n## unicode:')
print('Cyrillic: \u041a\u0438\u0440\u0438\u043b\u043b\u0438\u0446\u0430')
print('CJK: \u4f60\u597d\u4e16\u754c')

print('\n## All tests passed.')
