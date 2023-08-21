# pylint: disable=import-error,invalid-name,broad-except
import os.path as op

from pyrevit import HOST_APP
from pyrevit.framework import clr
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
from pyrevit.extensions import ICON_FILE_FORMAT, ICON_DARK_SUFFIX
from Autodesk.Revit.UI import UIThemeManager, UITheme


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


def is_infocenter_visible():
    return ad.ComponentManager.InfoCenterToolBar.Visibility == \
        Windows.Visibility.Visible


def toggle_infocenter():
    current_state = ad.ComponentManager.InfoCenterToolBar.Visibility
    is_hidden = (current_state == Windows.Visibility.Collapsed)
    ad.ComponentManager.InfoCenterToolBar.Visibility = \
        Windows.Visibility.Visible if is_hidden else \
            Windows.Visibility.Collapsed
    return is_infocenter_visible()


def get_ribbon_roottype():
    ap_assm = clr.GetClrType(ap.Windows.RibbonTabList).Assembly
    for apt in ap_assm.GetTypes():
        if 'PanelSetListView' in apt.Name:
            return apt


def get_current_theme():
    """
    Get the current UI theme.

    Returns:
        UITheme: The current UI theme.
    """
    return UIThemeManager.CurrentTheme

def set_current_theme(theme='Dark'):
    """
    Sets the current UI theme to either 'Dark' or 'Light'.

    Args:
        theme (str, optional): The theme to set. Defaults to 'Dark'.
    
    Returns:
        None
    """
    if theme = 'Dark':
        return UIThemeManager.CurrentTheme = UITheme.Dark
    else:
        return UIThemeManager.CurrentTheme = UITheme.Light


def resolve_icon_file(directory, icon_name):
    full_file_path = op.join(directory, icon_name)

    if HOST_APP.is_newer_than(2024, True) and get_current_theme() == UITheme.Dark:
        dark_icon_name = op.splitext(icon_name)[0] + ICON_DARK_SUFFIX + ICON_FILE_FORMAT
        dark_file_path = op.join(directory, dark_icon_name)
        full_file_path = dark_file_path if op.exists(dark_file_path) else full_file_path

    return full_file_path if op.exists(full_file_path) else None
