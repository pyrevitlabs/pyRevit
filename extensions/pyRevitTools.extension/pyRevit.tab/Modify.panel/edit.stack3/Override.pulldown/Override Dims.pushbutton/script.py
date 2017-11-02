"""Provides options for overriding values on selected dimensions."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


def add_plusminus():
    with revit.Transaction('add plusMinus to dims'):
        for elId in revit.uidoc.Selection.GetElementIds():
            el = revit.doc.GetElement(elId)
            if isinstance(el, DB.Dimension):
                if len(list(el.Segments)) > 0:
                    for seg in el.Segments:
                        seg.Prefix = u'\xb1'
                else:
                    el.Prefix = u'\xb1'


def override_dim_value():
    with revit.Transaction('Overrride dims value'):
        for elId in revit.uidoc.Selection.GetElementIds():
            el = revit.doc.GetElement(elId)
            if isinstance(el, DB.Dimension):
                if len(list(el.Segments)) > 0:
                    for seg in el.Segments:
                        exitingValue = seg.ValueString
                        seg.ValueOverride = u'\u200e' + exitingValue
                else:
                    exitingValue = el.ValueString
                    el.ValueOverride = u'\u200e' + exitingValue


def set_to_eq():
    with revit.Transaction('EQ dimensions'):
        for elId in revit.uidoc.Selection.GetElementIds():
            el = revit.doc.GetElement(elId)
            if isinstance(el, DB.Dimension):
                if len(list(el.Segments)) > 0:
                    for seg in el.Segments:
                        seg.ValueOverride = 'EQ'
                else:
                    el.ValueOverride = 'EQ'


def set_to_vfrmfr():
    with revit.Transaction('VWM dimensions'):
        for elId in revit.uidoc.Selection.GetElementIds():
            el = revit.doc.GetElement(elId)
            if isinstance(el, DB.Dimension):
                if len(list(el.Segments)) > 0:
                    for seg in el.Segments:
                        seg.Suffix = 'R.O.'
                        seg.Below = 'VERIFY W/ MFR'
                else:
                    el.Suffix = 'R.O.'
                    el.Below = 'VERIFY W/ MFR'


def set_to_vif():
    with revit.Transaction('VIF dimensions'):
        for elId in revit.uidoc.Selection.GetElementIds():
            el = revit.doc.GetElement(elId)
            if isinstance(el, DB.Dimension):
                if len(list(el.Segments)) > 0:
                    for seg in el.Segments:
                        seg.Below = 'VIF'
                else:
                    el.Below = 'VIF'


options = {'Add Plus/Minus': add_plusminus,
           'Bake Dimension Value': override_dim_value,
           'Set to EQ': set_to_eq,
           'Set to VIF MFR': set_to_vfrmfr,
           'Set to VIF': set_to_vif}

selected_switch = \
    forms.CommandSwitchWindow.show(sorted(options.keys()),
                                   message='Pick override option:')

if selected_switch:
    options[selected_switch]()
