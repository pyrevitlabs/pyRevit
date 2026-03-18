from pyrevit import forms
from match import panel

if not forms.is_registered_dockable_panel(panel.MatchHistoryClipboard):
    forms.register_dockable_panel(panel.MatchHistoryClipboard)
else:
    print("Skipped registering dockable pane. Already exists.")
