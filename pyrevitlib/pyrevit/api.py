"""Provide access to Revit API.

Example:
    >>> from pyrevit.api import AdWindows
    >>> from pyrevit.api import NSJson
"""

from pyrevit.framework import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('AdWindows')
clr.AddReference('UIFramework')
clr.AddReference('UIFrameworkServices')

import Autodesk.Internal as AdInternal
import Autodesk.Private as AdPrivate
import Autodesk.Windows as AdWindows

import UIFramework
import UIFrameworkServices

import Autodesk.Revit.Attributes as Attributes

import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI as UI

# try loading some utility modules shipped with revit
try:
    clr.AddReference('Newtonsoft.Json')
    import Newtonsoft.Json as NSJson
except Exception:
    pass
