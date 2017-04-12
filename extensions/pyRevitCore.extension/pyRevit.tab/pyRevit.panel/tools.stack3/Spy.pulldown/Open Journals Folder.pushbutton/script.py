"""Opens the Revit journals folder for current user."""


import os
from scriptutils import coreutils
import revitutils.journals as journals


__context__ = 'zerodoc'


journals_folder = journals.get_journals_folder()
coreutils.open_folder_in_explorer(journals_folder)
