#! python3
# -*- coding: utf-8 -*-
# pylint: skip-file

# set PYTHONPATH to ....\Lib\site-packages correctly

def print_html(output_str):
    print(output_str.replace('<', '&clt;').replace('>', '&cgt;'))

import sys
print(sys.version)
print("\n## sys.path:")
print('\n'.join(sys.path))

# test numpy
try:
    import numpy as np
    print("\n## numpy array:")
    print(repr(np.arange(15).reshape(3, 5)))
except Exception as ex:
    print('numpy load error: {}'.format(ex))

# test pandas
try:
    import pandas as pd

    df_dict = {'key 1': 1, 'key 2': 2, 'key 3': 3}
    df = pd.DataFrame([df_dict])

    print("\n## pandas DataFrame:")
    print_html(df.to_html().replace('\n', ''))
except Exception as ex:
    print(f'pandas load error: {ex}')


import clr
# clr.AddReference('Autodesk.Revit.DB')
import Autodesk.Revit.DB as DB

print('\n## UIApplication:')
__revit__ = sys.host
print(__revit__)

cl = DB.FilteredElementCollector(__revit__.ActiveUIDocument.Document)\
       .OfClass(DB.Wall)\
       .WhereElementIsNotElementType()\
       .ToElements()

print('\n## list of DB.Walls:')
for wall in cl:
    print(f'{wall} id:{wall.Id.IntegerValue}')

# test unicode
print("""
Кириллица (/ sɪˈrɪlɪk /) - это система письма
""")