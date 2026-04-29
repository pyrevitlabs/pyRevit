from pyrevit import forms, script
from match import panel

logger = script.get_logger()

if not forms.is_registered_dockable_panel(panel.MatchHistoryClipboard):
    forms.register_dockable_panel(panel.MatchHistoryClipboard, default_visible=False)
else:
    logger.debug("Skipped registering dockable pane. Already exists.")
