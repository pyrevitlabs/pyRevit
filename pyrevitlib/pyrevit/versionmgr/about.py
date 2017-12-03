# -*- coding: utf-8 -*-
from collections import namedtuple


PyRevitAbout = namedtuple('PyRevitAbout', ['subtitle',
                                           'madein',
                                           'copyright'])


def get_pyrevit_about():
    return PyRevitAbout(subtitle='python tools for Autodesk Revit®',
                        madein="['pdx', 'hio', 'rno']",
                        copyright='© 2015-2017 Ehsan Iran-Nejad')
