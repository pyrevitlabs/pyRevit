__doc__ = """Keep mirrored elements in current selection

Shift-Click: keep only not-Mirrored
"""
__context__ = 'Selection'

import inspect
from pyrevit import forms, script, revit, DB
from System.Collections.Generic import List

def is_mirrored(e):
    try:
        return e.Mirrored
    except:
        return False


if __name__ == '__main__':
    filtered = list(
        filter(lambda e: is_mirrored(e) != __shiftclick__, 
               revit.get_selection().elements))
    revit.get_selection().set_to(filtered)