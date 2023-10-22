"""Provide access to Revit API.

Examples:
    ```python
    from pyrevit.api import AdWindows
    ```
"""
import os.path as op

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
from Autodesk.Revit.DB import ExternalService
from Autodesk.Revit.DB import DirectContext3D


def get_product_serial_number():
    """Return serial number of running host instance.

    Returns:
        (str): Serial number
    """
    return UIFrameworkServices.InfoCenterService.ProductSerialNumber


def is_product_demo():
    """Determine if product is using demo license.

    Returns:
        (bool): True if product is using demo license
    """
    return get_product_serial_number() == '000-00000000'


def is_api_object(data_type):
    """Check if given object belongs to Revit API.

    Args:
        data_type (object): Object to check

    Returns:
        (bool): True if object belongs to Revit API
    """
    if hasattr(data_type, 'GetType'):
        return 'Autodesk.Revit.' in data_type.GetType().Namespace
