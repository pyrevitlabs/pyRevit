"""CPython stub backend for pyrevit.forms.

This module provides stub-only symbols. All stubs raise
PyRevitCPythonNotSupported with a stable feature name string and do not
load WPF/clr assemblies at import time.

Stubbed symbols:
WPFWindow, TemplateUserInputWindow, SelectFromList, CommandSwitchWindow,
ProgressBar, ask_for_string, ask_for_unique_string, ask_for_one_item,
ask_for_date, ask_for_number_slider, pick_file, pick_folder, show_balloon.
"""

from pyrevit import PyRevitCPythonNotSupported

__all__ = [
    "WPFWindow",
    "TemplateUserInputWindow",
    "SelectFromList",
    "CommandSwitchWindow",
    "ProgressBar",
    "ask_for_string",
    "ask_for_unique_string",
    "ask_for_one_item",
    "ask_for_date",
    "ask_for_number_slider",
    "pick_file",
    "pick_folder",
    "show_balloon",
]


def _raise_not_supported(feature_name):
    raise PyRevitCPythonNotSupported(feature_name)


class _NotSupportedBase(object):
    _feature_name = None

    def __init__(self, *args, **kwargs):
        _raise_not_supported(self._feature_name)

    @classmethod
    def _raise(cls, suffix=None):
        feature_name = cls._feature_name
        if suffix:
            feature_name = "{}.{}".format(feature_name, suffix)
        _raise_not_supported(feature_name)


class WPFWindow(_NotSupportedBase):
    _feature_name = "pyrevit.forms.WPFWindow"


class TemplateUserInputWindow(WPFWindow):
    _feature_name = "pyrevit.forms.TemplateUserInputWindow"

    @classmethod
    def show(cls, *args, **kwargs):
        cls._raise("show")


class SelectFromList(TemplateUserInputWindow):
    _feature_name = "pyrevit.forms.SelectFromList"


class CommandSwitchWindow(TemplateUserInputWindow):
    _feature_name = "pyrevit.forms.CommandSwitchWindow"


class ProgressBar(_NotSupportedBase):
    _feature_name = "pyrevit.forms.ProgressBar"


def ask_for_string(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.ask_for_string")


def ask_for_unique_string(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.ask_for_unique_string")


def ask_for_one_item(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.ask_for_one_item")


def ask_for_date(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.ask_for_date")


def ask_for_number_slider(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.ask_for_number_slider")


def pick_file(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.pick_file")


def pick_folder(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.pick_folder")


def show_balloon(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.show_balloon")
