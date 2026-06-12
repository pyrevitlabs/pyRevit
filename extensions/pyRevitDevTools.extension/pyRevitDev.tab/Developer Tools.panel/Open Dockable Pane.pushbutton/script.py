"""Prints calculated hash values for each extension."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens




from pyrevit import forms


test_panel_uuid = "3110e336-f81c-4927-87da-4e0d30d4d64a"

forms.open_dockable_panel(test_panel_uuid)
