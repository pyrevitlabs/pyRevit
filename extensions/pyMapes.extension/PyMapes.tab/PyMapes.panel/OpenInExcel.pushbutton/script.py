"""

Copyright (c) 2016 WeWork | Gui Talarico
Base script taken from pyRevit Respository.


"""

__doc__ = 'Opens Selected schedules in Excel'

from Autodesk.Revit.DB import ViewSchedule, ViewScheduleExportOptions
from Autodesk.Revit.DB import ExportColumnHeaders, ExportTextQualifier
from Autodesk.Revit.DB import BuiltInCategory, ViewSchedule
from Autodesk.Revit.UI import TaskDialog

import os
import subprocess

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

desktop = os.path.expandvars('%temp%\\')
# desktop = os.path.expandvars('%userprofile%\\desktop')

vseop = ViewScheduleExportOptions()
# vseop.ColumnHeaders = ExportColumnHeaders.None
# vseop.TextQualifier = ExportTextQualifier.None
# vseop.FieldDelimiter = ','
# vseop.Title = False

selected_ids = uidoc.Selection.GetElementIds()

if not selected_ids.Count:
    '''If nothing is selected, use Active View'''
    selected_ids=[ doc.ActiveView.Id ]

for element_id in selected_ids:
    element = doc.GetElement(element_id)
    if not isinstance(element, ViewSchedule):
        print('No schedule in Selection. Skipping...')
        continue

    filename = "".join(x for x in element.ViewName if x not in ['*']) + '.txt'
    element.Export(desktop, filename, vseop)

    print('EXPORTED: {0}\n      TO: {1}\n'.format(element.ViewName, filename))
    excel_paths = [
        r"C:\Program Files\Microsoft Office 15\root\office15\EXCEL.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
        r"C:\Program Files (x86)\Microsoft Office\Office14\EXCEL.exe",
        r"C:\Program Files (x86)\Microsoft Office\Office15\EXCEL.EXE",
        ]
    for excel in excel_paths:
        if os.path.exists(excel):
            print('Excel Found. Trying to open...')
            print('Filename is: ', filename)
            try:
                full_filepath = os.path.join(desktop, filename)
                os.system('start excel \"{path}\"'.format(path=full_filepath))
                __window__.Close()
                break
            except:
                print('Sorry, something failed:')
                print('Filepath: {}'.filename)
                print('excel Path: {}'.format(excel))
    else:
        print('Could not find excel. Paths: {}'.format(excel_paths))
