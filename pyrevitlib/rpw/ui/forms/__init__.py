"""
The forms module provide several pre-build forms as well as a framework
from which you can build your own forms.

All classes documented in this section can be imported as such:

>>> from rpw.ui.forms import Console

"""

# FlexForm + Componets
from rpw.ui.forms.flexform import FlexForm
from rpw.ui.forms.flexform import Label, TextBox, Button, ComboBox, CheckBox
from rpw.ui.forms.flexform import Separator

# Pre-built, easy to use FlexForms
from rpw.ui.forms.quickform import SelectFromList, TextInput

# Out-of-the Box TaskDialogs
from rpw.ui.forms.taskdialog import Alert, TaskDialog, CommandLink

# RPW Interactive Console
from rpw.ui.forms.console import Console

# Out-of-the Box TaskDialogs
from rpw.ui.forms.os_dialog import select_file, select_folder
