"""Print the full path to the central model (if model is workshared).

Shift+Click:
Open central model path in file browser
"""
#pylint: disable=E0401,invalid-name
import os.path as op

from pyrevit import revit, EXEC_PARAMS
from pyrevit import forms
from pyrevit import script


if forms.check_workshared(doc=revit.doc):
    central_path = revit.query.get_central_path(doc=revit.doc)
    if EXEC_PARAMS.config_mode:
        script.show_folder_in_explorer(op.dirname(central_path))
    else:
        print(central_path)
