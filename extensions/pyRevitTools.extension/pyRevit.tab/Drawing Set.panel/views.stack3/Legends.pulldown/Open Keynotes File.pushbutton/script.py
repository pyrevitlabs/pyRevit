"""Opens keynote source file used in this model."""

import os

from pyrevit import revit, DB, UI
from pyrevit import script

__author__ = 'Dan Mapes'
__contact__ = 'https://github.com/DMapes'


logger = script.get_logger()


kt = DB.KeynoteTable.GetKeynoteTable(revit.doc)
kt_ref = kt.GetExternalFileReference()
path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
    kt_ref.GetAbsolutePath()
    )

if not path:
    UI.TaskDialog.Show('pyrevit',
                       'No keynote file is assigned.')
else:
    os.system('start notepad "{0}"'.format(path))
