from pyrevit.framework import IntPtr

from pyrevit.api import AdInternal as ai
from pyrevit.api import AdPrivate as ap
from pyrevit.api import AdWindows as ad
from pyrevit.api import UIFramework as uf
from pyrevit.api import UIFrameworkServices as ufs

from pyrevit.coreutils.loadertypes import User32, RECT


__all__ = ['get_mainwindow_hwnd', 'get_statusbar_hwnd',
           'set_statusbar_text', 'get_window_rectangle']


def get_mainwindow_hwnd():
    return ad.ComponentManager.ApplicationWindow


def get_statusbar_hwnd():
    return User32.FindWindowEx(get_mainwindow_hwnd(),
                               IntPtr.Zero,
                               "msctls_statusbar32",
                               "")


def set_statusbar_text(text):
    statusBarPtr = get_statusbar_hwnd()

    if (statusBarPtr != IntPtr.Zero):
        User32.SetWindowText(statusBarPtr, text)
        return True

    return False


def get_window_rectangle():
    return User32.GetWindowRect(get_mainwindow_hwnd())
