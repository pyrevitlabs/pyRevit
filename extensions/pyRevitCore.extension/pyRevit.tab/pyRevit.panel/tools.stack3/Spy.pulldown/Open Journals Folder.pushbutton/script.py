"""Opens the Revit journals folder for current user."""


from pyrevit import coreutils
from pyrevit import revit


journals_folder = revit.get_journals_folder()
coreutils.open_folder_in_explorer(journals_folder)
