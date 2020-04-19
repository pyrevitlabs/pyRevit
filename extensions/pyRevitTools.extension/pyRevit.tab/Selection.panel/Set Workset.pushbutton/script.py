"""
This tool will set the active workset from the selected element's workset.
Copyright (c) 2020 Jean-Marc Couffin
https://github.com/jmcouffin
--------------------------------------------------------
pyRevit Notice:
Copyright (c) 2014-2020 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

__title__ = 'Set\nWorkset'
__author__ = 'Jean-Marc Couffin'
__context__ = 'selection'
__contact__ = 'https://github.com/jmcouffin'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'Sets the active workset from the selection'

#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit
from pyrevit import forms


# make sure doc is workshared
# if there is selection
if forms.check_workshared() and forms.check_selection():
    selection = revit.get_selection()
    # find element workset
    workset = revit.query.get_element_workset(selection.first)
    if workset:
        with revit.Transaction('Set Active Workset'):
            revit.update.set_active_workset(workset.Id, doc=revit.doc)
