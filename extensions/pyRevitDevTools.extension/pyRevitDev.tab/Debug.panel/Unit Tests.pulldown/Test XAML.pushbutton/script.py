"""Test loading XAML in IronPython."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import urllib2
import json
from time import sleep

from pyrevit import framework
from pyrevit import coreutils
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


class EmployeeInfo(forms.Reactive):
    def __init__(self, name, job, supports):
        self._name = name
        self._job = job
        self.supports = supports

    @forms.reactive
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @forms.reactive
    def job(self):
        return self._job

    @job.setter
    def job(self, value):
        self._job = value


class Server(forms.Reactive):
    def __init__(self, url):
        self.url = url
        self._status = False

    @forms.reactive
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value


class DataSelectorConverter(framework.Windows.Data.IMultiValueConverter):
    def Convert(self, values, target_types, parameter, culture):
        return values[0][int(values[1]) - 1]

    def ConvertBack(self, value, target_types, parameter, culture):
        pass


# code-behind for the window
class UI(forms.WPFWindow):
    def __init__(self):
        self.employee_data = [
            EmployeeInfo(
                name="Ehsan",
                job="Architect",
                supports=[
                    "UX",
                    "CLI",
                    "Core"
                ]),
            EmployeeInfo(
                name="Gui",
                job="Programmer",
                supports=[
                    "CLI",
                ]),
            EmployeeInfo(
                name="Alex",
                job="Designer",
                supports=[
                    "Core"
                ]),
        ]
        self.nested_data = NestedObject(text="Text in Data Object")
        self.data = \
            ButtonData(
                title="Title in Data Object",
                nested=self.nested_data
                )
        self.server = Server(r'https://status.epicgames.com/api/v2/status.json')

    def setup(self):
        mbinding = framework.Windows.Data.MultiBinding()
        mbinding.Converter = DataSelectorConverter()
        mbinding.Bindings.Add(framework.Windows.Data.Binding("."))
        binding = framework.Windows.Data.Binding("Value")
        binding.ElementName = "selector"
        mbinding.Bindings.Add(binding)
        # mbinding.NotifyOnSourceUpdated = True

        self.textbox.DataContext = self.nested_data
        self.emppanel.SetBinding(self.emppanel.DataContextProperty, mbinding)
        self.empinfo.DataContext = self.employee_data
        self.textblock.DataContext = self.data
        self.button.DataContext = self.data
        self.statuslight.DataContext = self.server

    def set_status(self, status):
        self.server.status = status is not None

    def check_status(self):
        status = json.loads(coreutils.read_url(self.server.url))
        sleep(2)    # fake slow io
        self.dispatch(self.set_status, status)

    def check_fortnite_status(self, sender, args):
        self.dispatch(self.check_status)

    def button_click(self, sender, args):
        self.data.title = "Title in Data Object (Updated)"
        self.nested_data.text = "Text in Data Object (Updated)"
        for emp in self.employee_data:
            emp.job = emp.job.replace(" (Updated)", "") + " (Updated)"

    def read_data(self, sender, args):
        forms.alert(self.nested_data.text)

# init ui
ui = script.load_ui(UI(), 'ui.xaml')
# show modal or nonmodal
ui.show_dialog()
