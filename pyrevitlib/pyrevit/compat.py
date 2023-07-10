"""python engine compatibility module.

Example:
    >>> from pyrevit.compat import IRONPY277
    >>> from pyrevit.compat import safe_strtype
"""

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
IRONPY273 = sys.version_info[:3] == (2, 7, 3)
IRONPY277 = sys.version_info[:3] == (2, 7, 7)
IRONPY278 = sys.version_info[:3] == (2, 7, 8)
IRONPY279 = sys.version_info[:3] == (2, 7, 9)
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


#pylint: disable=C0103
safe_strtype = str
if PY2:
    # https://gist.github.com/gornostal/1f123aaf838506038710
    safe_strtype = lambda x: unicode(x)  #pylint: disable=E0602,unnecessary-lambda


def urlopen(url):
    """urlopen wrapper"""
    if PY3:
        return urllib.request.urlopen(url)
    return urllib2.urlopen(url)


def make_request(url, headers, data):
    """urlopen wrapper to create and send a request"""
    if PY3:
        req = urllib.request.Request(url, headers, data)
        urllib.request.urlopen(req).close()
        return

    req = urllib2.Request(url, headers, data)
    urllib2.urlopen(req).close()
