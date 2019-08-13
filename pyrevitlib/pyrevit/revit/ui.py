from pyrevit.framework import IntPtr

#pylint: disable=W0611
from pyrevit import HOST_APP
from pyrevit.api import AdInternal as ai
from pyrevit.api import AdPrivate as ap
from pyrevit.api import AdWindows as ad
from pyrevit.api import UIFramework as uf
from pyrevit.api import UIFrameworkServices as ufs

from pyrevit.coreutils.basetypes import User32, RECT


__all__ = ('get_mainwindow_hwnd', 'get_statusbar_hwnd',
           'set_statusbar_text', 'get_window_rectangle')


def get_mainwindow_hwnd():
    return HOST_APP.proc_window


def get_statusbar_hwnd():
    return User32.FindWindowEx(get_mainwindow_hwnd(),
                               IntPtr.Zero,
                               "msctls_statusbar32",
                               "")


def set_statusbar_text(text):
    status_bar_ptr = get_statusbar_hwnd()

    if status_bar_ptr != IntPtr.Zero:
        User32.SetWindowText(status_bar_ptr, text)
        return True

    return False


def get_window_rectangle():
    return User32.GetWindowRect(get_mainwindow_hwnd())
