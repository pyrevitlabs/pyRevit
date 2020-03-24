"""Provide access to Revit API.

Example:
    >>> from pyrevit.api import AdWindows
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
from Autodesk.Revit import ApplicationServices
from Autodesk.Revit import DB
from Autodesk.Revit import UI


# grab the interal PanelSetListView type
PANELLISTVIEW_TYPE = None
ADPRIVATE_ASSM = clr.GetClrType(AdPrivate.Windows.RibbonTabList).Assembly
for apt in ADPRIVATE_ASSM.GetTypes():
    if 'PanelSetListView' in apt.Name:
        PANELLISTVIEW_TYPE = apt
        break


def get_product_serial_number():
    """Return serial number of running host instance."""
    return UIFrameworkServices.InfoCenterService.ProductSerialNumber


def is_product_demo():
    """Determine if product is using demo license"""
    return get_product_serial_number() == '000-00000000'


def is_api_object(data_type):
    """Check if given object belongs to Revit API"""
    if hasattr(data_type, 'GetType'):
        return 'Autodesk.Revit.' in data_type.GetType().Namespace
