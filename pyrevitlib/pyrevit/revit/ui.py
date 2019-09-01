#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import HOST_APP
from pyrevit.framework import IntPtr
from pyrevit.framework import Interop, Windows
from pyrevit.api import AdInternal as ai
from pyrevit.api import AdPrivate as ap
from pyrevit.api import AdWindows as ad
from pyrevit.api import UIFramework as uf
from pyrevit.api import UIFrameworkServices as ufs
from pyrevit.labs import Common
from pyrevit.runtime import types
from pyrevit.coreutils import envvars


def get_mainwindow_hwnd():
    return HOST_APP.proc_window


def get_mainwindow():
    try:
        hwnd_source = Interop.HwndSource.FromHwnd(HOST_APP.proc_window)
        return hwnd_source.RootVisual
    except Exception:
        pass


def get_statusbar_hwnd():
    return Common.User32.FindWindowEx(
        get_mainwindow_hwnd(),
        IntPtr.Zero,
        "msctls_statusbar32",
        "")


def set_statusbar_text(text):
    status_bar_ptr = get_statusbar_hwnd()

    if status_bar_ptr != IntPtr.Zero:
        Common.User32.SetWindowText(status_bar_ptr, text)
        return True

    return False


def get_window_rectangle():
    return Common.User32.GetWindowRect(get_mainwindow_hwnd())


def toggle_infocenter(state):
    ad.ComponentManager.InfoCenterToolBar.Visibility = \
        Windows.Visibility.Visible if state else \
            Windows.Visibility.Collapsed


def toggle_doc_colorizer(state):
    uiapp = HOST_APP.uiapp
    if HOST_APP.is_newer_than(2018):
        # cancel out the colorizer from previous runtime version
        current_tabcolorizer = \
            envvars.get_pyrevit_env_var(envvars.TABCOLORIZER_ENVVAR)
        if current_tabcolorizer:
            current_tabcolorizer.StopGroupingDocumentTabs(uiapp)

        # start or stop the document colorizer
        if state:
            types.DocumentTabEventUtils.StartGroupingDocumentTabs(uiapp)
        else:
            types.DocumentTabEventUtils.StopGroupingDocumentTabs(uiapp)

        # set the new colorizer
        envvars.set_pyrevit_env_var(
            envvars.TABCOLORIZER_ENVVAR,
            types.DocumentTabEventUtils
            )
