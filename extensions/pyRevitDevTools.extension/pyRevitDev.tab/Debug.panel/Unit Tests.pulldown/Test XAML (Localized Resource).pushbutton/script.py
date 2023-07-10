"""Test loading XAML in IronPython."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import urllib2
import json
from time import sleep
import sys
import threading

import os.path as op
from pyrevit import EXEC_PARAMS

from pyrevit import framework
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()

class UI(forms.WPFWindow, forms.Reactive):
    def __init__(self):
        pass

# init ui
ui = script.load_ui(UI(), 'ui.xaml')
# show modal or nonmodal
ui.show_dialog()
