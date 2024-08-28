"""python engine compatibility module.

Examples:
    ```python
    from pyrevit.compat import IRONPY2711
    from pyrevit.compat import safe_strtype
    ```
"""

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
IRONPY2712 = sys.version_info[:3] == (2, 7, 12)
IRONPY340 = sys.version_info[:3] == (3, 4, 0)

#pylint: disable=import-error,unused-import
if PY3:
    __builtins__["unicode"] = str

if PY2:
    import _winreg as winreg
    import ConfigParser as configparser
    from collections import Iterable
    import urllib2
    from urlparse import urlparse

elif PY3:
    import winreg as winreg
    import configparser as configparser
    from collections.abc import Iterable
    import urllib
    from urllib.parse import urlparse


def is_netcore():
    """Returns True if the current Revit version uses .NET Core (from 2025 onward)."""
    if __revit__ is None:
        return False
    netcore_version = 2025
    try:
        # UIApplication
        return int(__revit__.Application.VersionNumber) >= netcore_version
    except AttributeError:
        pass
    try:
        # Application, (ControlledApplication)
        return int(__revit__.VersionNumber) >= netcore_version
    except AttributeError:
        # UIControlledApplication
        return int(__revit__.ControlledApplication.VersionNumber) >= netcore_version


#pylint: disable=C0103
safe_strtype = str
if PY2:
    # https://gist.github.com/gornostal/1f123aaf838506038710
    safe_strtype = lambda x: unicode(x)  #pylint: disable=E0602,unnecessary-lambda


def get_value_func():
        """Determines and returns the appropriate value extraction function based on the host application's version.

        Returns:
            function: A function that takes an item as an argument and returns its value. 
                      If the host application version is newer than 2023, it returns the `get_value_2024` function, 
                      which extracts the `Value` attribute from the item. 
                      Otherwise, it returns the `get_value_2003` function, which extracts the `IntegerValue` attribute from the item.
    
        Functions:
            get_value_2024(item): Extracts the `Value` attribute from the given item.
            get_value_2003(item): Extracts the `IntegerValue` attribute from the given item.
        
        Examples:
            ```python
            value_func = get_value_func()
            sheet_revids = {value_func(x) for x in self.revit_sheet.GetAllRevisionIds()}
            add_sheet_revids = {value_func(x) x in self.revit_sheet.GetAdditionalRevisionIds()}
            ```
        """
        def get_value_2024(item):
            return item.Value
    
        def get_value_2003(item):
            return item.IntegerValue
    
        return get_value_2024 if __revit__.Application.is_newer_than(2023) else get_value_2003


def urlopen(url):
    """Urlopen wrapper.

    Args:
        url (str): request url
    """
    if PY3:
        return urllib.request.urlopen(url)
    return urllib2.urlopen(url)


def make_request(url, headers, data):
    """Urlopen wrapper to create and send a request.

    Args:
        url (str): request url
        headers (dict[str, str]): headers
        data (bytes | None): request data
    """
    if PY3:
        req = urllib.request.Request(url, headers, data)
        urllib.request.urlopen(req).close()
        return

    req = urllib2.Request(url, headers, data)
    urllib2.urlopen(req).close()
