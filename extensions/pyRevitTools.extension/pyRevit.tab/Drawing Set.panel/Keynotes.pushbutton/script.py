"""Manage project keynotes."""
#pylint: disable=E0401,W0613,C0111,C0103
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__title__ = "Manage\nKeynotes"
__author__ = "{{author}}"
__context__ = ""

logger = script.get_logger()
output = script.get_output()


class KeynoteManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._read_keynotes()

    def _read_keynotes(self):
        knote_file = revit.query.get_keynote_file()

    def search_txt_changed(self, sender, args):
        pass

    def clear_search(self, sender, args):
        pass


KeynoteManagerWindow('KeynoteManagerWindow.xaml').show(modal=True)
