from pyrevit._perf import mark as _perfmark, time_block as _perfblock
_perfmark("startup.pyRevitTools:entry")

from pyrevit import forms, script
from customprops.custom_props_pane import CONFIG_SECTION, CustomPropertiesPanel
_perfmark("startup.pyRevitTools:after `from pyrevit import forms, script`")

from match import clipboard
_perfmark("startup.pyRevitTools:after `from match import panel`")

logger = script.get_logger()

if not forms.is_registered_dockable_panel(clipboard.MatchHistoryClipboard):
    with _perfblock("startup.pyRevitTools:register_dockable_panel(MatchHistoryClipboard)"):
        forms.register_dockable_panel(clipboard.MatchHistoryClipboard, default_visible=False)
else:
    logger.debug("Skipped registering dockable pane. Already exists.")

my_config = script.get_config(CONFIG_SECTION)
if my_config.get_option("enabled", False):
    if not forms.is_registered_dockable_panel(CustomPropertiesPanel):
        forms.register_dockable_panel(CustomPropertiesPanel, default_visible=False)
    else:
        logger.debug("Skipped registering Custom Properties pane. Already exists.")
else:
    logger.debug("Custom Properties pane disabled in config. Enable via Shift+Click the button.")

_perfmark("startup.pyRevitTools:exit")
