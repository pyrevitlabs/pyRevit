"""Developer example: a command that acts on what a checkbox stored.

The Saved Setting checkbox can only store its state, because checkbox
handlers run outside Revit API context. A command runs in API context, so
this is where a tool would read the setting and change the model.
"""

from pyrevit import forms

import devtools_examples_settings

state = "on" if devtools_examples_settings.is_enabled("saved_setting") else "off"
forms.alert(
    "The Saved Setting checkbox is {}.".format(state), title="Show Saved Setting"
)
