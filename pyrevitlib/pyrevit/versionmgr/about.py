# -*- coding: utf-8 -*-
from collections import namedtuple


PyRevitAbout = namedtuple('PyRevitAbout', ['subtitle',
                                           'madein',
                                           'copyright'])


def get_pyrevit_about():
    return PyRevitAbout(subtitle='python RAD Environment for Autodesk Revit®',
                        madein="['pdx', 'hio', 'rno']",
                        copyright='© 2014-2019 Ehsan Iran-Nejad')
