#! python3
# pylint: skip-file

# PYTHONPATH = C:\Program Files\Python35\Lib\site-packages
import sys
print('\n'.join(sys.path))

# try:
#     import numpy as np
#     print(repr(np.arange(15).reshape(3, 5)))
# except Exception as ex:
#     print('numpy load error: {}'.format(ex))


import clr
# clr.AddReference('Autodesk.Revit.DB')
import Autodesk.Revit.DB as DB

__revit__ = sys.host
print(__revit__)

cl = DB.FilteredElementCollector(__revit__.ActiveUIDocument.Document)\
       .OfClass(DB.Wall)\
       .WhereElementIsNotElementType()\
       .ToElements()

for wall in cl:
    print(wall)
