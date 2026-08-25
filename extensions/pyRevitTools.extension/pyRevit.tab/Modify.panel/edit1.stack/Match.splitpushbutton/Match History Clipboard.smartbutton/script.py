from pyrevit import forms
from pyrevit.revit import ui
from pyrevit.framework import Threading, System
import pyrevit.extensions as exts
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from match import clipboard


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):

    def set_icon(is_shown):
        if is_shown:
            icon = ui.resolve_icon_file(script_cmp.directory, exts.DEFAULT_ON_ICON_FILE)
        else:
            icon = ui.resolve_icon_file(
                script_cmp.directory, exts.DEFAULT_OFF_ICON_FILE
            )
        ui_button_cmp.set_icon(icon, icon_size=ICON_MEDIUM)

    def update_icon_from_pane():
        try:
            if forms.is_registered_dockable_panel(clipboard.MatchHistoryClipboard):
                dockable = forms.get_dockable_panel(clipboard.MatchHistoryClipboard)
                set_icon(dockable.IsShown())
            else:
                set_icon(False)
        except Exception:
            set_icon(False)

    def on_visibility_changed(sender, args):
        def deferred():
            update_icon_from_pane()

        Threading.Dispatcher.CurrentDispatcher.BeginInvoke(
            Threading.DispatcherPriority.Background, System.Action(deferred)
        )

    def on_document_opened(sender, args):
        __rvt__.Application.DocumentOpened -= on_document_opened
        update_icon_from_pane()
        __rvt__.DockableFrameVisibilityChanged += on_visibility_changed

    set_icon(False)

    try:
        if __rvt__.ActiveUIDocument is not None:
            update_icon_from_pane()
            __rvt__.DockableFrameVisibilityChanged += on_visibility_changed
        else:
            __rvt__.Application.DocumentOpened += on_document_opened
    except Exception:
        __rvt__.Application.DocumentOpened += on_document_opened

    return True


if __name__ == "__main__":
    if forms.is_registered_dockable_panel(clipboard.MatchHistoryClipboard):
        dockable_panel = forms.get_dockable_panel(clipboard.MatchHistoryClipboard)
        forms.toggle_dockable_panel(
            clipboard.MatchHistoryClipboard, not dockable_panel.IsShown()
        )
