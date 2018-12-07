"""Opens keynote source file used in this model."""

import os

from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


__author__ = 'Dan Mapes\n{{author}}'
__contact__ = 'https://github.com/DMapes'


path = revit.query.get_keynote_file()
if not path:
    forms.alert('No keynote file is assigned.')
else:
    os.system('start notepad "{0}"'.format(path))
