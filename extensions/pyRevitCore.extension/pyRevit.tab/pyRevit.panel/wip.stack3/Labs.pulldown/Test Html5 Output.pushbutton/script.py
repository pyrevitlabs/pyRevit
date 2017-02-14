import clr
import sys
import os
import os.path as op

clr.AddReferenceByPartialName('System.Windows.Forms')
import System.Windows.Forms

sys.path.append(r'C:\Users\eirannejad\Desktop\awm')
clr.AddReference('Awesomium.Core')
clr.AddReference('awesomium')
clr.AddReference('Awesomium.Windows.Forms')
import Awesomium


class HTMLFiveWindow:
    def __init__(self):
        self.win = System.Windows.Forms.Form()
        settings = cef.CefSettings()
        settings.CachePath = r'C:\Users\eirannejad\Desktop\cef\cache'
        settings.BrowserSubprocessPath = r'C:\Users\eirannejad\Desktop\cef'

        cef.Cef.Initialize(settings)
        browser = cef.WinForms.ChromiumWebBrowser("www.google.com")
        self.win.Controls.Add(browser)
        browser.Dock = System.Windows.Forms.DockStyle.Fill
    def show(self):
        self.win.ShowDialog()


HTMLFiveWindow().show()

# import clr
# import sys
# import os
# import os.path as op
#
# clr.AddReferenceByPartialName('System.Windows.Forms')
# import System.Windows.Forms
#
# cef_folder = r'C:\Users\eirannejad\Desktop\cef'
# sys.path.append(cef_folder)
# clr.AddReference('CefSharp')
# clr.AddReference('CefSharp.Core')
# clr.AddReference('CefSharp.WinForms')
# import CefSharp as cef
#
#
# class HTMLFiveWindow:
#     def __init__(self):
#         self.win = System.Windows.Forms.Form()
#         settings = cef.CefSettings()
#         settings.CachePath = r'C:\Users\eirannejad\Desktop\cef\cache'
#         settings.BrowserSubprocessPath = r'C:\Users\eirannejad\Desktop\cef'
#
#         cef.Cef.Initialize(settings)
#         browser = cef.WinForms.ChromiumWebBrowser("www.google.com")
#         self.win.Controls.Add(browser)
#         browser.Dock = System.Windows.Forms.DockStyle.Fill
#     def show(self):
#         self.win.ShowDialog()
#
#
# HTMLFiveWindow().show()
