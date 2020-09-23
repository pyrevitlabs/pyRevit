"""Provide access to Revit API.

Example:
    >>> from pyrevit.api import AdWindows
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


BIM_360_SCHEMA = 'BIM 360://'


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


def expand_bim360_path(path):
    """Converts BIM 360 to local path"""
    if path.startswith(BIM_360_SCHEMA):
        return op.expandvars(
            op.normpath(
                path.replace(BIM_360_SCHEMA, '%HOMEPATH%/BIM 360/')
            )
        )
    return path
