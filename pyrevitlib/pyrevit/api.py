"""Provide access to Revit API.

Example:
    >>> from pyrevit.api import AdWindows
    >>> from pyrevit.api import NSJson
"""

#pylint: disable=E0401,W0611,W0703,C0413
from pyrevit.framework import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('AdWindows')
clr.AddReference('UIFramework')
clr.AddReference('UIFrameworkServices')

import UIFramework
import UIFrameworkServices

import Autodesk.Internal as AdInternal
import Autodesk.Private as AdPrivate
import Autodesk.Windows as AdWindows

from Autodesk.Revit import Attributes
from Autodesk.Revit import DB
from Autodesk.Revit import UI

# try loading some utility modules shipped with revit
try:
    clr.AddReference('Newtonsoft.Json')
    import Newtonsoft.Json as NSJson
except Exception:
    pass
