from pyrevit import forms, script
from match import panel


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # TODO: This isn't working. No clue why.
    is_shown = False
    try:
        if forms.is_registered_dockable_panel(panel.MatchHistoryClipboard):
            dockable_panel = forms.get_dockable_panel(panel.MatchHistoryClipboard)
            forms.toggle_dockable_panel(
                panel.MatchHistoryClipboard, not dockable_panel.IsShown()
            )
            script.toggle_icon(dockable_panel.IsShown())
    except Exception:
        is_shown = False
    script.toggle_icon(is_shown)


if forms.is_registered_dockable_panel(panel.MatchHistoryClipboard):
    dockable_panel = forms.get_dockable_panel(panel.MatchHistoryClipboard)
    forms.toggle_dockable_panel(
        panel.MatchHistoryClipboard, not dockable_panel.IsShown()
    )
    script.toggle_icon(dockable_panel.IsShown())
