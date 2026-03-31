from pyrevit import forms, script
from match import panel


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # TODO: This isn't working. No clue why.
    is_shown = False
    # try:
    #     if forms.is_registered_dockable_panel(panel.MatchHistoryClipboard):
    #         dockable_panel = forms.get_dockable_panel(panel.MatchHistoryClipboard)
    #         is_shown = dockable_panel.IsShown()
    # except Exception:
    #     pass

    script.toggle_icon(is_shown)
    # init must return true if successful
    return True


if forms.is_registered_dockable_panel(panel.MatchHistoryClipboard):
    dockable_panel = forms.get_dockable_panel(panel.MatchHistoryClipboard)
    forms.toggle_dockable_panel(
        panel.MatchHistoryClipboard, not dockable_panel.IsShown()
    )
    script.toggle_icon(dockable_panel.IsShown())
