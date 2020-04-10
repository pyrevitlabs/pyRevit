"""
This tool will set the active workset from the element\'s workset in the selection.
Copyright (c) 2020 Jean-Marc Couffin
https://github.com/jmcouffin
--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2019 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

__title__ = 'Set Active Workset'
__author__ = 'Jean-Marc Couffin'
__contact__ = 'https://github.com/jmcouffin'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'This tool will set the active workset from the element\'s workset in the selection '

from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms

logger = script.get_logger()

selection = revit.get_selection()
elements = []

if len(selection) == 1:
    for el in selection:
        elements.append(revit.doc.GetWorksetTable().GetWorkset((el).WorksetId).Id)
    with revit.Transaction('Set active workset'):
        for el in elements:
            ActiveWs = revit.doc.GetWorksetTable().SetActiveWorksetId(el)
else:
    forms.alert('One element must be selected.')