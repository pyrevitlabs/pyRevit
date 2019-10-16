"""Test loading XAML in IronPython."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


class NestedObject(forms.Reactive):
    def __init__(self, text):
        self._text = text

    @forms.reactive
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value


class ButtonData(forms.Reactive):
    def __init__(self, title, nested):
        self._title = title
        self.nested = nested

    @forms.reactive
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value


# code-behind for the window
class UI(forms.WPFWindow):
    def __init__(self):
        self.nested_data = NestedObject(text="<nested text>")
        self.data = \
            ButtonData(
                title="<bound title>",
                nested=self.nested_data
                )

    def setup(self):
        self.textbox.DataContext = self.nested_data
        self.textblock.DataContext = self.data
        self.button.DataContext = self.data

    def update_text(self, sender, args):
        pass

    def button_click(self, sender, args):
        self.data.title = "<updated bound title>"
        self.nested_data.text = "<updated nested text>"

    def read_data(self, sender, args):
        forms.alert(self.nested_data.text)


# init ui
ui = script.load_ui(UI(), 'ui.xaml')
# show modal or nonmodal
ui.show_dialog()