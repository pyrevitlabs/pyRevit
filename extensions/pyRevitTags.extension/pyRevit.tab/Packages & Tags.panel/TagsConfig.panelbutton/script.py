"""Tags configuration options."""
#pylint: disable=C0111,E0401,C0103,W0613,W0703
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


class TagsConfigsWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)


TagsConfigsWindow('TagsConfigsWindow.xaml').ShowDialog()
