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
IRONPY2 = PY2 and '.net' in sys.version.lower()
IRONPY3 = PY3 and '.net' in sys.version.lower()
NETCORE = System.Environment.Version.Major >= 8  # Revit 2025 onwards
NETFRAMEWORK = not NETCORE # Revit 2024 and earlier

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

#pylint: disable=C0103
safe_strtype = str
if PY2:
    # https://gist.github.com/gornostal/1f123aaf838506038710
    safe_strtype = lambda x: unicode(x)  #pylint: disable=E0602,unnecessary-lambda


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
