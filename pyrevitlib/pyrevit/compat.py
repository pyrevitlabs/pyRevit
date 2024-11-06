"""python engine compatibility module.

Examples:
    ```python
    from pyrevit.compat import IRONPY2711
    from pyrevit.compat import safe_strtype
    ```
"""

import sys
import System

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
IRONPY = '.net' in sys.version.lower()
IRONPY2 = PY2 and IRONPY
IRONPY3 = PY3 and IRONPY
NETCORE = System.Environment.Version.Major >= 8  # Revit 2025 onwards
NETFRAMEWORK = not NETCORE # Revit 2024 and earlier
NO_REVIT = -1
REVIT_NETCORE_VERSION = 2025

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


def _get_revit_version():
    """Returns the current Revit version as an integer."""
    if __revit__ is None:
        return NO_REVIT
    try:
        # UIApplication
        return int(__revit__.Application.VersionNumber)
    except AttributeError:
        pass
    try:
        # Application, (ControlledApplication)
        return int(__revit__.VersionNumber)
    except AttributeError:
        # ControlledApplication
        return int(__revit__.ControlledApplication.VersionNumber)


#pylint: disable=C0103
safe_strtype = str
if PY2:
    # https://gist.github.com/gornostal/1f123aaf838506038710
    safe_strtype = lambda x: unicode(x)  #pylint: disable=E0602,unnecessary-lambda


def get_elementid_value_func():
    """Returns the ElementId value extraction function based on the Revit version.
    
    Follows API changes in Revit 2024.

    Returns:
        function: A function returns the value of an ElementId.

    Examples:
        ```python
        get_elementid_value = get_elementid_value_func()
        sheet_revids = {get_elementid_value(x) for x in self.revit_sheet.GetAllRevisionIds()}
        add_sheet_revids = {get_elementid_value(x) x in self.revit_sheet.GetAdditionalRevisionIds()}
        ```
    """
    def get_value_post2024(item):
        return item.Value

    def get_value_pre2024(item):
        return item.IntegerValue

    return get_value_post2024 if _get_revit_version() > 2023 else get_value_pre2024


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
