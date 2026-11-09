from pyrevit import DB, UI, forms
from pyrevit.revit import events, ui
from pyrevit.framework import Threading, System
import pyrevit.extensions as exts
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from panes.clipboard.pane import MatchHistoryClipboard

_DOC_OPENED_SLOT = "pyRevitTools.MatchHistoryClipboard.DocumentOpened"
_VISIBILITY_SLOT = "pyRevitTools.MatchHistoryClipboard.DockableFrameVisibilityChanged"


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
            if forms.is_registered_dockable_panel(MatchHistoryClipboard):
                dockable = forms.get_dockable_panel(MatchHistoryClipboard)
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

    def watch_visibility():
        events.replace_handler(
            _VISIBILITY_SLOT,
            __rvt__,
            "DockableFrameVisibilityChanged",
            on_visibility_changed,
            UI.Events.DockableFrameVisibilityChangedEventArgs,
        )

    def wait_for_document():
        events.replace_handler(
            _DOC_OPENED_SLOT,
            __rvt__.Application,
            "DocumentOpened",
            on_document_opened,
            DB.Events.DocumentOpenedEventArgs,
        )

    def on_document_opened(sender, args):
        events.release_handler(_DOC_OPENED_SLOT, __rvt__.Application, "DocumentOpened")
        update_icon_from_pane()
        watch_visibility()

    set_icon(False)
    events.release_handler(_DOC_OPENED_SLOT, __rvt__.Application, "DocumentOpened")
    events.release_handler(_VISIBILITY_SLOT, __rvt__, "DockableFrameVisibilityChanged")

    try:
        if __rvt__.ActiveUIDocument is not None:
            update_icon_from_pane()
            watch_visibility()
        else:
            wait_for_document()
    except Exception:
        wait_for_document()

    return True


if __name__ == "__main__":
    if forms.is_registered_dockable_panel(MatchHistoryClipboard):
        dockable_panel = forms.get_dockable_panel(MatchHistoryClipboard)
        forms.toggle_dockable_panel(MatchHistoryClipboard, not dockable_panel.IsShown())
