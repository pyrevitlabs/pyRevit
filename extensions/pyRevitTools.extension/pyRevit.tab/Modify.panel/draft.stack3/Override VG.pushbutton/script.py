"""Provides options for overriding Visibility/Graphics on selected elements."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


selection = revit.get_selection()


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
    with revit.Transaction('Whiteout Selected Elements'):
        for el in selection:
            if isinstance(el, DB.Group):
                for mem in el.GetMemberIds():
                    selection.append(revit.doc.GetElement(mem))
            ogs = DB.OverrideGraphicSettings()
            ogs.SetProjectionLineColor(DB.Color(255, 255, 255))
            revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)


options = {'Halftone Selected': halftone,
           'Reset VG Overrides': reset_vg,
           'Solid-Line Selected': solid_line,
           'White-out Selected': whiteout}

selected_switch = \
    forms.CommandSwitchWindow.show(
        sorted(options.keys()),
        message='Pick Visibility/Graphics override option:'
        )

if selected_switch:
    options[selected_switch]()
