"""UI functions."""
#pylint: disable=import-error,invalid-name,broad-except
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


def get_mainwindow_hwnd():
    """
    Get the handle of the main window.

    Returns:
        (intptr): The handle of the main window.
    """
    return HOST_APP.proc_window


def get_mainwindow():
    """Get the main window of the application.

    Returns:
        The root visual of the main window.
    """
    try:
        hwnd_source = Interop.HwndSource.FromHwnd(HOST_APP.proc_window)
        return hwnd_source.RootVisual
    except Exception:
        pass


def get_statusbar_hwnd():
    """Retrieves the handle of the status bar control belonging to the main window.

    Returns:
        (IntPtr): The handle of the status bar control.
    """
    return Common.User32.FindWindowEx(
        get_mainwindow_hwnd(),
        IntPtr.Zero,
        "msctls_statusbar32",
        "")


def set_statusbar_text(text):
    """Sets the text of the status bar.

    Parameters:
        text (str): The text to be displayed in the status bar.

    Returns:
        bool: True if the text was successfully set, False otherwise.
    """
    status_bar_ptr = get_statusbar_hwnd()

    if status_bar_ptr != IntPtr.Zero:
        Common.User32.SetWindowText(status_bar_ptr, text)
        return True

    return False


def get_window_rectangle():
    """Get the rectangle coordinates of the main window.

    Returns:
        (Tuple[int, int, int, int]): The left, top, right, and bottom 
            coordinates of the window rectangle.
    """
    return Common.User32.GetWindowRect(get_mainwindow_hwnd())


def is_infocenter_visible():
    """
    Check if the InfoCenter toolbar is visible.

    Returns:
        (bool): True if the InfoCenter toolbar is visible, False otherwise.
    """
    return ad.ComponentManager.InfoCenterToolBar.Visibility == \
        Windows.Visibility.Visible


def toggle_infocenter():
    """
    Toggles the visibility of the InfoCenter toolbar.

    This function retrieves the current visibility state of the InfoCenter 
    toolbar and toggles it to the opposite state.
    If the toolbar is currently collapsed, it will be set to visible,
    and if it is currently visible, it will be set to collapsed.
    The function then returns the visibility state of the InfoCenter toolbar
    after the toggle operation.

    Returns:
        (bool): True if the InfoCenter toolbar is visible, False otherwise.
    """
    current_state = ad.ComponentManager.InfoCenterToolBar.Visibility
    is_hidden = (current_state == Windows.Visibility.Collapsed)
    ad.ComponentManager.InfoCenterToolBar.Visibility = \
        Windows.Visibility.Visible if is_hidden else \
            Windows.Visibility.Collapsed
    return is_infocenter_visible()


def get_ribbon_roottype():
    """Get the type of the ribbon root.

    Returns:
        (type): type of the ribbon root
    """
    ap_assm = clr.GetClrType(ap.Windows.RibbonTabList).Assembly
    for apt in ap_assm.GetTypes():
        if 'PanelSetListView' in apt.Name:
            return apt
