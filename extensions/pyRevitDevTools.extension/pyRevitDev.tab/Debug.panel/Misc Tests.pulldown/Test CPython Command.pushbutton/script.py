#! python3
# pylint: skip-file

# PYTHONPATH = C:\Program Files\Python35\Lib\site-packages
import sys
print('\n'.join(sys.path))


def print_html(output_str):
    print(output_str.replace('<', '&clt;').replace('>', '&cgt;'))


# trst numpy
try:
    import numpy as np
    print(repr(np.arange(15).reshape(3, 5)))
except Exception as ex:
    print('numpy load error: {}'.format(ex))

# trst pandas
try:
    import pandas as pd

    df_dict = {'key 1': 1, 'key 2': 2, 'key 3': 3}
    df = pd.DataFrame([df_dict])

    print("pandas dataframe:")
    print(print_html(df.to_html()))
except Exception as ex:
    print('pandas load error: {}'.format(ex))



def print_html(output_str):
	print(output_str.replace('<', '&clt;').replace('>', '&cgt;'))

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
