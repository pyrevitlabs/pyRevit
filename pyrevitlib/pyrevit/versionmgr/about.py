# -*- coding: utf-8 -*-
"""Utility module for pyRevit project information.

Examples:
        ```python
        from pyrevit.versionmgr import about
        a = about.get_pyrevit_about()
        a.subtitle
        ```
        'python RAD Environment for Autodesk Revit®'a.copyright'© 2014-2025 Ehsan Iran-Nejad'
"""
from collections import namedtuple


# FIXME: tuple attrs have duplicate docs
PyRevitAbout = namedtuple('PyRevitAbout', ['subtitle', 'madein', 'copyright'])
"""pyRevit project info tuple.

Attributes:
    subtitle (str): project subtitle
    madein (str): project made-in info
    copyright (str): project copyright info
"""


def get_pyrevit_about():
    """Return information about pyRevit project.

    Returns:
        (PyRevitAbout): pyRevit project info tuple
    """
    return PyRevitAbout(subtitle='python RAD Environment for Autodesk Revit®',
                        madein="['pdx', 'hio', 'rno', 'sea']",
                        copyright='© 2014-2025 Ehsan Iran-Nejad')
