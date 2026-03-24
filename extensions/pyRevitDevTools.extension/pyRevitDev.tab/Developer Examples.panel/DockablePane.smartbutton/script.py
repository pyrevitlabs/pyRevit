# -*- coding: utf-8 -*-
"""Developer sample: WPFPanel smartbutton.

Exercises every WPFPanel / _WPFMixin feature.
The toolbar icon mirrors the panel's open/closed state.
"""

from pyrevit import forms, script, PyRevitException


dev_sample_guid = "759a2751-290a-4f7a-8f2d-9d900b2547b8"

_NOT_REGISTERED_MSG = (
    "The sample dockable pane is not registered. Register it from this "
    "extension's startup.py on UIControlledApplication (before running "
    "this button)."
)


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):

    is_shown = False
    try:
        _panel = forms.get_dockable_panel(dev_sample_guid)
        is_shown = _panel.IsShown()
    except Exception:
        is_shown = False
    # TODO FIXME: toggle_icon doesn't work. no idea why. debug shows it can't find the ui_button.
    script.toggle_icon(is_shown)


try:
    _panel = forms.get_dockable_panel(dev_sample_guid)
    forms.toggle_dockable_panel(dev_sample_guid, not _panel.IsShown())
    script.toggle_icon(_panel.IsShown())
except PyRevitException:
    forms.alert(_NOT_REGISTERED_MSG)
