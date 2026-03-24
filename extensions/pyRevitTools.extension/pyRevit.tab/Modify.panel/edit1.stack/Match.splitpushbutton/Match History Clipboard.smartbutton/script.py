from pyrevit import forms, script, coreutils, HOST_APP
from pyrevit import UI


clipboard_pane_guid = "0f3a0866-0123-4178-9f2c-121961bd292c"


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    is_shown = False
    try:
        dpanel_id = UI.DockablePaneId(coreutils.Guid.Parse(clipboard_pane_guid))
        if UI.DockablePane.PaneIsRegistered(dpanel_id):
            dockable_panel = HOST_APP.uiapp.GetDockablePane(dpanel_id)
            if dockable_panel is not None:
                is_shown = dockable_panel.IsShown()
    except Exception:
        is_shown = False
    script.toggle_icon(is_shown)


dpanel_id = UI.DockablePaneId(coreutils.Guid.Parse(clipboard_pane_guid))
if UI.DockablePane.PaneIsRegistered(dpanel_id):
    dockable_panel = HOST_APP.uiapp.GetDockablePane(dpanel_id)
    if dockable_panel is not None:
        forms.toggle_dockable_panel(clipboard_pane_guid, not dockable_panel.IsShown())
        script.toggle_icon(dockable_panel.IsShown())
