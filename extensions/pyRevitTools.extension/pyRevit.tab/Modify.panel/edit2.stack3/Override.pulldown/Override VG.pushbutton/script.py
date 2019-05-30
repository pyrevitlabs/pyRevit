"""Provides options for overriding Visibility/Graphics on selected elements.

Shift-Click: Override Cut pattern also"""
#pylint: disable=E0401,C0103
import re
from collections import OrderedDict

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__context__ = 'selection'


logger = script.get_logger()

selection = revit.get_selection()
# select all individual elements inside a group
selection.expand_groups()


def find_solid_fillpat():
    existing_pats = DB.FilteredElementCollector(revit.doc)\
                      .OfClass(DB.FillPatternElement)\
                      .ToElements()
    for pat in existing_pats:
        fpat = pat.GetFillPattern()
        if fpat.IsSolidFill and fpat.Target == DB.FillPatternTarget.Drafting:
            return pat


def colorvg(r, g, b, projline_only=False, xacn_name=None):
    color = DB.Color(r, g, b)
    with revit.Transaction(xacn_name or 'Set Color VG override'):
        for el in selection:
            if isinstance(el, DB.Group):
                for mem in el.GetMemberIds():
                    selection.append(revit.doc.GetElement(mem))
            ogs = DB.OverrideGraphicSettings()
            ogs.SetProjectionLineColor(color)
            if __shiftclick__:
                ogs.SetCutLineColor(color)
            if not projline_only:
                ogs.SetProjectionFillColor(color)
                if __shiftclick__:
                    ogs.SetCutFillColor(color)
                solid_fpattern = find_solid_fillpat()
                if solid_fpattern:
                    ogs.SetProjectionFillPatternId(solid_fpattern.Id)
                    if __shiftclick__:
                        ogs.SetCutFillPatternId(solid_fpattern.Id)
                else:
                    logger.warning('Can not find solid fill pattern in model'
                                   'to assign as projection/cut pattern.')
            revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)


def halftone():
    with revit.Transaction('Halftone Elements in View'):
        for el in selection:
            if isinstance(el, DB.Group):
                for mem in el.GetMemberIds():
                    selection.append(revit.doc.GetElement(mem))
            ogs = DB.OverrideGraphicSettings()
            ogs.SetHalftone(True)
            # ogs.SetProjectionFillPatternVisible(False)
            revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)


def reset_vg():
    with revit.Transaction('Reset Element Override'):
        for el in selection:
            ogs = DB.OverrideGraphicSettings()
            revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)


def solid_line():
    with revit.Transaction("Set Element to Solid Projection Line Pattern"):
        for el in selection:
            if el.ViewSpecific:
                ogs = DB.OverrideGraphicSettings()
                ogs.SetProjectionLinePatternId(
                    DB.LinePatternElement.GetSolidPatternId()
                    )
                revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)


def whiteout():
    # 0xffffff
    colorvg(0xff, 0xff, 0xff,
            projline_only=True,
            xacn_name='Whiteout Selected Elements')


def mark_red():
    # 0xff5714
    colorvg(0xff, 0x57, 0x14,
            xacn_name='Mark Selected with Red')


def mark_green():
    # 0x6eeb83
    colorvg(0x6e, 0xeb, 0x83,
            xacn_name='Mark Selected with Green')


def mark_orange():
    # 0xffb800
    colorvg(0xff, 0xb8, 0x00,
            xacn_name='Mark Selected with Orange')


def mark_blue():
    # 0x1be7ff
    colorvg(0x1b, 0xe7, 0xff,
            xacn_name='Mark Selected with Yello')


options = OrderedDict([('Reset VG Overrides', reset_vg),
                       ('Halftone Selected', halftone),
                       ('Solid-Line Selected', solid_line),
                       ('White-out Selected', whiteout),
                       ('Solid-Red Selected', mark_red),
                       ('Solid-Green Selected', mark_green),
                       ('Solid-Orange Selected', mark_orange),
                       ('Solid-Blue Selected', mark_blue)])


selected_switch = \
    forms.CommandSwitchWindow.show(
        options.keys(),
        config={'Halftone Selected': {'background': '0xaaaaaa'},
                'Solid-Red Selected': {'background': '0xff5714'},
                'Solid-Green Selected': {'background': '0x6eeb83'},
                'Solid-Orange Selected': {'background': '0xffb800'},
                'Solid-Blue Selected': {'background': '0x1be7ff'}},
        message='Pick Visibility/Graphics override option:'
        )

if selected_switch:
    options[selected_switch]()
