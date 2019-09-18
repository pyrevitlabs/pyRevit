#! python3
# # -*- coding: utf-8 -*-
# pylint: skip-file
# set PYTHONPATH to ....\Lib\site-packages correctly
def print_html(output_str):
    print(output_str.replace('<', '&clt;').replace('>', '&cgt;'))

import sys
print(sys.version)
print("\n## sys.path:")
print('\n'.join(sys.path))


# print globals
print('\n## This file (__file__):')
print('__file__ = %s' % __file__)
print('\n## This scope (__name__):')
print('__name__ = %s' % __name__)

print('\n## UIApplication: (__revit__)')
print('__revit__ = %s' % __revit__)

print('\n## pyRevit globals:')
print('__execid__ = %s' % __execid__)
print('__timestamp__ = %s' % __timestamp__)
print('__cachedengine__ = %s' % __cachedengine__)
print('__cachedengineid__ = %s' % __cachedengineid__)
print('__scriptruntime__ = %s' % __scriptruntime__)
print('__commanddata__ = %s' % __commanddata__)
print('__elements__ = %s' % __elements__)
print('__commandpath__ = %s' % __commandpath__)
print('__configcommandpath__ = %s' % __configcommandpath__)
print('__commandname__ = %s' % __commandname__)
print('__commandbundle__ = %s' % __commandbundle__)
print('__commandextension__ = %s' % __commandextension__)
print('__commanduniqueid__ = %s' % __commanduniqueid__)
print('__forceddebugmode__ = %s' % __forceddebugmode__)
print('__shiftclick__ = %s' % __shiftclick__)

print('__result__ = %s' % __result__)

print('__eventsender__ = %s' % __eventsender__)
print('__eventargs__ = %s' % __eventargs__)


print('\n## Module Tests:')
# try tkinter
try:
    import tkinter
    print('tkinter is included')
except Exception as ex:
    print('tkinter load error: {}'.format(ex))

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


print('\n## Revit Document Tests:')
import clr
# clr.AddReference('Autodesk.Revit.DB')
import Autodesk.Revit.DB as DB

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

import pyrevit
from pyrevit import revit

print('\n## pyrevit.revit:')

for el in revit.get_selection():
    print(el)


# """This is the tooltip content"""

# from pyrevit import forms

# selected_switch, switches = \
#     forms.CommandSwitchWindow.show(
#         ['Option_1', 'Option 2', 'Option 3', 'Option 4', 'Option 5'],
#         switches=['Switch 1', 'Switch 2'],
#         message='Select Option:',
#         recognize_access_key=True
#         )

# if selected_switch:
#     print('Try different Modifier keys with '
#           'this button to check results. '
#           '\n Selected Option: {}'
#           '\n Switch 1 = {}'
#           '\n Switch 2 = {}'.format(selected_switch,
#                                     switches['Switch 1'],
#                                     switches['Switch 2']))



from System.Collections.Generic import List

selected_ids = revit.uidoc.Selection.GetElementIds()

selected_ids_list = List[DB.ElementId]()
for eid in selected_ids:
    selected_ids_list.Add(eid)

if selected_ids:
    collector = DB.FilteredElementCollector(revit.doc, selected_ids_list)\
                .OfClass(DB.Wall)\
                .WhereElementIsNotElementType()
    for w in collector:
        print(w)
