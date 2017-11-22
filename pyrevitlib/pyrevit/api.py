from pyrevit.framework import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('AdWindows')
clr.AddReference('UIFramework')
clr.AddReference('UIFrameworkServices')
clr.AddReference('Newtonsoft.Json')

import Autodesk.Internal as AdInternal
import Autodesk.Private as AdPrivate
import Autodesk.Windows as AdWindows

import UIFramework
import UIFrameworkServices

import Newtonsoft.Json as NSJson

import Autodesk.Revit.Attributes as Attributes

import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI as UI
