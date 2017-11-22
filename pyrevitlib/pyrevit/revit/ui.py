from pyrevit.framework import IntPtr

from pyrevit.api import AdInternal as ai
from pyrevit.api import AdPrivate as ap
from pyrevit.api import AdWindows as ad
from pyrevit.api import UIFramework as uf
from pyrevit.api import UIFrameworkServices as ufs

from pyrevit.coreutils.loadertypes import User32


class RevitStatusBar(object):
    @staticmethod
    def GetStatusBarHwnd():
        return User32.FindWindowEx(ad.ComponentManager.ApplicationWindow,
                                   IntPtr.Zero,
                                   "msctls_statusbar32",
                                   "")

    @staticmethod
    def SetStatusText(text):
        statusBarPtr = RevitStatusBar.GetStatusBarHwnd()

        if (statusBarPtr != IntPtr.Zero):
            User32.SetWindowText(statusBarPtr, text)
            return True

        return False
