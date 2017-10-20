"""Opens the Revit journals folder for current user."""


from pyrevit import coreutils
from pyrevit.revit import journals


journals_folder = journals.get_journals_folder()
coreutils.open_folder_in_explorer(journals_folder)
