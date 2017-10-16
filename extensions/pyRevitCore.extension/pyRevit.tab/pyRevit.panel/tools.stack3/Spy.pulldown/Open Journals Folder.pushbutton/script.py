"""Opens the Revit journals folder for current user."""


from pyrevit import coreutils
from pyrevit import revitjournals


journals_folder = revitjournals.get_journals_folder()
coreutils.open_folder_in_explorer(journals_folder)
